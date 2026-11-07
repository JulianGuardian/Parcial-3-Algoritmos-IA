"""Event freshness (spec: stale events are not trusted).

Age is measured from an event's `recorded_at` to the response's
`_meta.retrieved_at`, never to the wall clock, so results are reproducible.
"""

from datetime import datetime, timedelta, timezone

DEFAULT_MAX_EVENT_AGE = timedelta(hours=2)


def parse_utc(timestamp: str) -> datetime:
    """Parse an ISO 8601 UTC timestamp such as `2026-09-15T10:48:00Z`."""
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def ensure_utc(moment: datetime) -> datetime:
    """Treat a naive datetime as UTC so it can be compared with tool timestamps."""
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment


def is_stale(
    recorded_at: datetime,
    retrieved_at: datetime,
    max_age: timedelta = DEFAULT_MAX_EVENT_AGE,
) -> bool:
    """An event is stale when it is strictly older than `max_age`."""
    return retrieved_at - recorded_at > max_age
