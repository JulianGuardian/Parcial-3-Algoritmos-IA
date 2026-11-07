import pytest

from app.disruption.assessment.sources import get_operational_events, get_trip_context
from app.disruption.contracts import BookingNotFound, ToolUnavailable


def test_trip_context_has_contract_shape():
    trip = get_trip_context("ABC123")

    assert trip["booking_id"] == "ABC123"
    assert {p["passenger_id"] for p in trip["passengers"]} == {"P1", "P2"}
    assert [s["segment_id"] for s in trip["segments"]] == ["S1", "S2"]
    assert set(trip["fare_conditions"]) >= {"changeable", "refundable", "fare_family"}
    assert trip["_meta"]["completeness"] == "PARTIAL"
    assert trip["_meta"]["retrieved_at"].endswith("Z")


def test_unknown_booking_raises_not_found():
    with pytest.raises(BookingNotFound):
        get_trip_context("NOPE99")


def test_operational_events_have_contract_shape():
    response = get_operational_events(["S1", "S2"])

    assert {e["event_id"] for e in response["events"]} == {"E-1001", "E-1007", "E-1012", "E-2003"}
    for event in response["events"]:
        assert {"event_id", "segment_id", "type", "source", "recorded_at"} <= set(event)
    assert response["_meta"]["sources_degraded"] == ["LEGACY_MIRROR"]


def test_operational_events_filter_by_segment():
    response = get_operational_events(["S2"])
    assert [e["event_id"] for e in response["events"]] == ["E-2003"]


def test_operational_events_require_segments():
    with pytest.raises(ToolUnavailable):
        get_operational_events([])


def test_adapters_return_independent_copies():
    first = get_trip_context("ABC123")
    first["passengers"].clear()
    assert len(get_trip_context("ABC123")["passengers"]) == 2
