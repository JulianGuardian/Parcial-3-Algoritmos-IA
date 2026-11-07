import json
from dataclasses import asdict
from datetime import datetime

from app.disruption.contracts import (
    AssessmentStatus,
    Decision,
    DiscardedEvent,
    DiscardReason,
    FareConditions,
    MissingField,
    Option,
    PassengerView,
    RejectedOption,
    RejectionReason,
    ResolveRequest,
    RuleResult,
    SegmentState,
    SegmentStatus,
    TraceEntry,
    TripState,
)


def test_resolve_request_defaults():
    request = ResolveRequest(booking_id="ABC123")
    assert request.now is None
    assert request.question is None
    assert request.compensation_requested is False
    assert request.wants_same_day is False


def test_trip_state_sample():
    state = TripState(
        booking_id="ABC123",
        party_size=2,
        has_minor=True,
        passengers=[PassengerView("P1", "María", "ADULT", masked_email="m***@example.com")],
        fare_conditions=FareConditions(changeable=True, refundable=False, fare_family="LIGHT"),
        segments=[
            SegmentState(
                segment_id="S1",
                flight_number="NB500",
                origin="SCL",
                destination="LIM",
                status=SegmentStatus.DELAYED,
                delay_minutes=160,
                estimated_arrival=datetime(2026, 9, 15, 20, 35),
            )
        ],
        assessment_status=AssessmentStatus.OK,
        relevant=True,
        relevance_reasons=["MISSED_CONNECTION"],
        discarded_events=[DiscardedEvent("E-1012", DiscardReason.DEGRADED_SOURCE)],
        missing_fields=["fare_conditions.change_penalty_amount"],
        trace=[TraceEntry("reconcile", "S1 delayed", {"segment": "S1"})],
    )
    assert state.segments[0].missed_connection is False
    assert state.trace[0].data == {"segment": "S1"}


def test_decision_sample():
    option = Option("O1", "REBOOK", policy_ref="POL-DELAY-2026-03", confidence="HIGH")
    rejected = RejectedOption(
        "O2",
        (RejectionReason.INSUFFICIENT_SEATS, RejectionReason.POLICY_INCONSISTENT),
        "1 seat for 2 passengers",
    )
    decision = Decision(
        booking_id="ABC123",
        policy_ref="POL-DELAY-2026-03",
        applied_rules=[RuleResult("R3", "REBOOK_NO_FEE", True, "missed_connection is true")],
        not_applied_rules=[RuleResult("R1", "REBOOK_NO_FEE", False, "160 < 180")],
        recommended_option=option,
        rejected_options=[rejected],
        missing_fields=[MissingField("fare_conditions.change_penalty_amount", False)],
        requires_human=True,
        human_reasons=["R5_PRIORITY_HANDLING"],
    )
    assert decision.auto_deliverable is False
    assert decision.rejected_options[0].reason is RejectionReason.INSUFFICIENT_SEATS


def test_contracts_serialise_without_personal_data():
    state = TripState(
        booking_id="ABC123",
        party_size=1,
        has_minor=False,
        passengers=[PassengerView("P1", "María", "ADULT")],
    )
    payload = json.dumps(asdict(state), default=str)
    assert "document_id" not in payload
