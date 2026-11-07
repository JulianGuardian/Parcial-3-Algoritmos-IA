from app.disruption.contracts import (
    AppliedRule,
    Decision,
    RejectedOption,
    ResolveRequest,
    SegmentState,
    TraceEntry,
    TripState,
)


def test_can_construct_one_sample_of_each_contract():
    request = ResolveRequest(booking_id="ABC123")
    segment = SegmentState(
        segment_id="S1",
        flight_number="NB500",
        status="DELAYED",
        delay_minutes=160,
        estimated_arrival="2026-09-15T20:35:00",
        missed_connection=True,
    )
    trip = TripState(
        booking_id="ABC123",
        party_size=2,
        has_minor=True,
        segments=[segment],
        assessment_status="OK",
        relevant=True,
    )
    rejected = RejectedOption(option_id="O2", reason="INSUFFICIENT_SEATS")
    decision = Decision(
        booking_id="ABC123",
        applied_rules=[AppliedRule(rule_id="R3", entitlement="REBOOK_NO_FEE")],
        not_applied_rules=[],
        policy_ref="POL-DELAY-2026-03",
        recommended_option={"option_id": "O1"},
        rejected_options=[rejected],
        requires_human=True,
        human_reasons=["R5_PRIORITY_HANDLING"],
        auto_deliverable=False,
    )
    trace = TraceEntry(step="assessment", detail={"ok": True})

    assert request.booking_id == "ABC123"
    assert trip.segments[0].missed_connection is True
    assert decision.rejected_options[0].option_id == "O2"
    assert trace.step == "assessment"
