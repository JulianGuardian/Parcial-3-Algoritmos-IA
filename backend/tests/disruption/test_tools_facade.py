import inspect
from datetime import datetime, timezone

from app.disruption.agents.tools import DisruptionToolsFacade
from app.disruption.assessment.service import assess_trip
from app.disruption.assessment.sources import get_operational_events, get_trip_context
from app.disruption.contracts import ResolveRequest
from app.disruption.entitlements.service import decide
from app.disruption.entitlements.sources import get_eligible_options, get_policy_rules

NOW = datetime(2026, 9, 15, 11, 3, 0, tzinfo=timezone.utc)


def _abc123_facade() -> DisruptionToolsFacade:
    trip = assess_trip(get_trip_context("ABC123"), get_operational_events(["S1", "S2"]))
    decision = decide(
        trip,
        policy=get_policy_rules("DELAY"),
        options_response=get_eligible_options({"booking_id": trip.booking_id}),
        request=ResolveRequest(trip.booking_id),
        now=NOW,
    )
    return DisruptionToolsFacade(trip, decision)


def test_abc123_summary_has_no_discarded_event_or_personal_data():
    facade = _abc123_facade()
    summary = facade.get_trip_summary()

    dumped = str(summary)
    assert "E-1012" not in dumped
    assert "LEGACY_MIRROR" not in dumped
    assert "document_id" not in dumped
    assert "maria.silva@example.com" not in dumped
    assert "12.345.678-9" not in dumped

    s2 = next(s for s in summary["segments"] if s["segment_id"] == "S2")
    assert s2["missed_connection"] is True


def test_entitlements_show_o1_r3_r5_and_policy_with_no_rejected_details():
    facade = _abc123_facade()
    entitlements = facade.get_entitlements()

    assert entitlements["recommended_option"]["option_id"] == "O1"
    assert "R3" in entitlements["applied_rules"]
    assert "R5" in entitlements["applied_rules"]
    assert entitlements["policy_ref"] == "POL-DELAY-2026-03"

    dumped = str(entitlements)
    assert "O2" not in dumped
    assert "O3" not in dumped
    assert entitlements["rejected_option_count"] >= 1


def test_no_tool_accepts_booking_id():
    facade = _abc123_facade()
    for method in (facade.get_trip_summary, facade.get_entitlements, facade.get_policy_rule):
        params = inspect.signature(method).parameters
        assert "booking_id" not in params
        assert "passenger_id" not in params
