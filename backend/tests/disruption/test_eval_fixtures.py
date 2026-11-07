from datetime import datetime, timezone

from app.disruption.assessment.service import assess_trip
from app.disruption.assessment.sources import get_operational_events, get_trip_context
from app.disruption.contracts import AssessmentStatus, ResolveRequest, SegmentStatus
from app.disruption.entitlements.service import decide
from app.disruption.entitlements.sources import get_eligible_options, get_policy_rules

NOW = datetime(2026, 9, 15, 11, 3, 0, tzinfo=timezone.utc)


def evaluate(booking_id):
    trip = get_trip_context(booking_id)
    state = assess_trip(trip, get_operational_events([s["segment_id"] for s in trip["segments"]]))
    decision = decide(
        state,
        policy=get_policy_rules("DELAY"),
        options_response=get_eligible_options(trip),
        request=ResolveRequest(booking_id),
        now=NOW,
    )
    return state, decision


def test_def456_is_adult_only_with_o1_and_no_human():
    state, decision = evaluate("DEF456")

    assert state.party_size == 1 and state.has_minor is False
    assert state.segments[1].missed_connection is True
    assert decision.recommended_option.option_id == "O1"
    assert decision.requires_human is False
    assert decision.auto_deliverable is True


def test_ghi789_has_contradictory_trusted_sources():
    state, decision = evaluate("GHI789")

    assert state.segments[0].status is SegmentStatus.CONFLICTING
    assert state.assessment_status is AssessmentStatus.CONFLICTING
    assert decision.recommended_option is None
    assert decision.requires_human is True
    assert decision.human_reasons == ["ASSESSMENT_CONFLICTING"]


def test_def456_pipeline_never_rebooks_without_confirmation():
    from app.disruption.actions.write_tools import REBOOKING, MockWriteTools
    from app.disruption.pipeline import resolve_disruption

    tools = MockWriteTools()

    resolution = resolve_disruption(ResolveRequest("DEF456", now=NOW), write_tools=tools)

    assert tools.calls_to(REBOOKING) == []
    assert resolution.actions.human_case is None
    assert "Please confirm this option" in resolution.message.text
