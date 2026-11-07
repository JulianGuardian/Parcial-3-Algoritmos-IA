from dataclasses import replace
from datetime import datetime, timezone

from app.disruption.assessment.service import assess_trip
from app.disruption.contracts import (
    AssessmentStatus,
    RejectionReason,
    ResolveRequest,
)
from app.disruption.entitlements.service import decide
from app.disruption.entitlements.sources import get_eligible_options, get_policy_rules

from .conftest import events_response, make_event

NOW = datetime(2026, 9, 15, 11, 3, 0, tzinfo=timezone.utc)


def run(state, *, compensation_requested=False, now=NOW, refetch=None, options=None):
    return decide(
        state,
        policy=get_policy_rules("DELAY"),
        options_response=options or get_eligible_options({"booking_id": state.booking_id}),
        request=ResolveRequest(state.booking_id, compensation_requested=compensation_requested),
        now=now,
        refetch_options=refetch,
    )


def test_abc123_recommends_o1_and_needs_a_human(abc123_state):
    decision = run(abc123_state)

    assert decision.policy_ref == "POL-DELAY-2026-03"
    assert decision.recommended_option.option_id == "O1"
    assert decision.recommended_option.flight_number == "NB2412"
    assert decision.requires_human is True
    assert decision.human_reasons == ["R5_PRIORITY_HANDLING"]
    assert decision.auto_deliverable is False


def test_abc123_rules_and_rejections(abc123_state):
    decision = run(abc123_state)

    assert [r.rule_id for r in decision.applied_rules] == ["R3", "R5"]
    assert [r.rule_id for r in decision.not_applied_rules] == ["R1", "R2", "R4"]
    rejected = {r.option_id: r for r in decision.rejected_options}
    assert rejected["O2"].reason is RejectionReason.INSUFFICIENT_SEATS
    assert rejected["O3"].reasons == (RejectionReason.REQUIRES_AGENT_REVIEW,)
    assert {t.step for t in decision.trace} >= {"rules", "options", "human_gate"}


def test_compensation_request_adds_r4(abc123_state):
    decision = run(abc123_state, compensation_requested=True)

    assert decision.human_reasons == ["R4_CASH_COMPENSATION", "R5_PRIORITY_HANDLING"]
    assert decision.requires_human is True
    assert decision.recommended_option.option_id == "O1"  # explanation kept, execution gated


def test_missing_change_penalty_is_listed_but_not_decision_relevant(abc123_state):
    decision = run(abc123_state)

    assert [(m.name, m.decision_relevant) for m in decision.missing_fields] == [
        ("fare_conditions.change_penalty_amount", False)
    ]
    assert "MISSING_DECISION_DATA" not in decision.human_reasons


def test_decision_relevant_missing_data_requires_a_human(abc123_state):
    from app.disruption.entitlements import service

    original = service.REQUIRED_FIELDS["REBOOK_NO_FEE"]
    service.REQUIRED_FIELDS["REBOOK_NO_FEE"] = frozenset({"fare_conditions.change_penalty_amount"})
    try:
        decision = run(abc123_state)
    finally:
        service.REQUIRED_FIELDS["REBOOK_NO_FEE"] = original

    assert decision.missing_fields[0].decision_relevant is True
    assert "MISSING_DECISION_DATA" in decision.human_reasons


def test_without_a_minor_or_compensation_the_rebooking_is_auto_deliverable(abc123_state):
    state = replace(abc123_state, has_minor=False)

    decision = run(state)

    assert decision.human_reasons == []
    assert decision.requires_human is False
    assert decision.auto_deliverable is True


def test_conflicting_assessment_escalates_without_recommendation(trip):
    events = events_response(
        [
            make_event("A", "S1", "CANCELLATION", "OPS_CORE", "2026-09-15T10:00:00Z"),
            make_event("B", "S1", "DELAY", "AIRPORT_FEED", "2026-09-15T10:50:00Z", delay_minutes=90),
        ]
    )
    state = assess_trip(trip, events)
    assert state.assessment_status is AssessmentStatus.CONFLICTING

    decision = run(state)

    assert decision.requires_human is True
    assert decision.human_reasons == ["ASSESSMENT_CONFLICTING"]
    assert decision.recommended_option is None
    assert decision.applied_rules == []


def test_unverified_assessment_escalates(trip):
    events = events_response(
        [make_event("OLD", "S1", "DELAY", "OPS_CORE", "2026-09-15T07:00:00Z", delay_minutes=160)]
    )
    decision = run(assess_trip(trip, events))

    assert decision.human_reasons == ["ASSESSMENT_UNVERIFIED"]
    assert decision.recommended_option is None


def test_informational_change_evaluates_no_entitlement(trip):
    events = events_response([make_event("G", "S1", "GATE_CHANGE", "AIRPORT_FEED", "2026-09-15T10:55:00Z", gate="24")])
    decision = run(assess_trip(trip, events))

    assert decision.applied_rules == [] and decision.not_applied_rules == []
    assert decision.policy_ref is None
    assert decision.requires_human is False
    assert decision.recommended_option is None


def test_expired_options_are_refetched_once_then_rejected(abc123_state):
    late = datetime(2026, 9, 15, 11, 5, 0, tzinfo=timezone.utc)
    calls = []

    def refetch():
        calls.append(1)
        return get_eligible_options({"booking_id": "ABC123"})  # the mock stays stale

    decision = run(abc123_state, now=late, refetch=refetch)

    assert calls == [1]
    assert decision.recommended_option is None
    assert {r.reason for r in decision.rejected_options} == {RejectionReason.EXPIRED}
    # Only the spec's gate conditions escalate: the minor still does, nothing else is added.
    assert decision.human_reasons == ["R5_PRIORITY_HANDLING"]


def test_fresh_refetch_recovers_the_recommendation(abc123_state):
    late = datetime(2026, 9, 15, 11, 5, 0, tzinfo=timezone.utc)

    def refetch():
        fresh = get_eligible_options({"booking_id": "ABC123"})
        fresh["_meta"]["retrieved_at"] = "2026-09-15T11:04:50Z"
        return fresh

    assert run(abc123_state, now=late, refetch=refetch).recommended_option.option_id == "O1"


def test_unknown_airport_blocks_the_decision(abc123_state):
    abc123_state.segments[0].origin = "ZZZ"
    abc123_state.segments[0].delay_minutes = 300

    decision = run(abc123_state)

    assert "MISSING_DECISION_DATA" in decision.human_reasons
    assert ("airport_country:ZZZ", True) in [(m.name, m.decision_relevant) for m in decision.missing_fields]
