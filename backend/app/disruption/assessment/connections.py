"""Estimated times and missed-connection detection (design D5).

Times are airport-local wall-clock values taken as given. The flight duration
is assumed unchanged, so a delay shifts departure and arrival by the same
amount.
"""

from datetime import datetime, timedelta

from app.disruption.contracts import SegmentState, SegmentStatus

DEFAULT_MIN_CONNECTION_MINUTES = 60


def parse_local(date: str, clock: str) -> datetime:
    """`("2026-09-15", "17:55")` -> naive datetime in airport-local time."""
    return datetime.fromisoformat(f"{date}T{clock}")


def schedule(date: str, departure: str, arrival: str) -> tuple[datetime, datetime]:
    """Scheduled departure and arrival; an earlier arrival clock means next day."""
    dep = parse_local(date, departure)
    arr = parse_local(date, arrival)
    if arr < dep:
        arr += timedelta(days=1)
    return dep, arr


def apply_estimates(
    segments: list[SegmentState],
    min_connection_minutes: int = DEFAULT_MIN_CONNECTION_MINUTES,
) -> None:
    """Fill estimated times and `missed_connection` in place.

    Estimates are only asserted for segments whose status is verified; an
    UNVERIFIED or CONFLICTING segment never produces a missed connection.
    """
    for segment in segments:
        if segment.status in (SegmentStatus.UNVERIFIED, SegmentStatus.CONFLICTING, SegmentStatus.CANCELLED):
            continue
        shift = timedelta(minutes=segment.delay_minutes)
        segment.estimated_departure = segment.scheduled_departure + shift
        segment.estimated_arrival = segment.scheduled_arrival + shift

    minimum = timedelta(minutes=min_connection_minutes)
    for previous, following in zip(segments, segments[1:]):
        if previous.estimated_arrival is None or previous.destination != following.origin:
            continue
        departure = following.estimated_departure or following.scheduled_departure
        following.missed_connection = departure < previous.estimated_arrival + minimum
