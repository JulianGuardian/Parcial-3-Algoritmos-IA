"""Mock read adapters for the trip and operational-event tools.

They return the raw tool-response shapes from the exam statement, loaded from
the fixtures. Real adapters would replace these two functions.
"""

from typing import Any

from app.disruption.contracts import BookingNotFound, ToolUnavailable
from app.disruption.fixtures import load_fixture

_KNOWN_BOOKINGS = {"ABC123": "get_trip_context_ABC123"}


def get_trip_context(booking_id: str) -> dict[str, Any]:
    """`get_trip_context(booking_id)`: passengers, segments, fare and `_meta`."""
    fixture = _KNOWN_BOOKINGS.get(booking_id)
    if fixture is None:
        raise BookingNotFound(booking_id)
    return load_fixture(fixture)


def get_operational_events(segment_ids: list[str]) -> dict[str, Any]:
    """`get_operational_events(segment_ids)`: events for those segments only."""
    if not segment_ids:
        raise ToolUnavailable("get_operational_events requires at least one segment id")
    response = load_fixture("get_operational_events_S1_S2")
    wanted = set(segment_ids)
    response["events"] = [e for e in response["events"] if e["segment_id"] in wanted]
    return response
