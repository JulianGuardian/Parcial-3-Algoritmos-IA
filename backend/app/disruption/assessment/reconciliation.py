"""Source reconciliation for one segment (design D3).

Rules, in order:
1. Events from a degraded source never count (`DEGRADED_SOURCE`).
2. Stale events never assert a status (`STALE`).
3. Within one source the most recent event wins.
4. Across sources, priority OPS_CORE > AIRPORT_FEED > LEGACY_MIRROR decides,
   except that OPS_CORE and AIRPORT_FEED (the trusted pair) disagreeing is a
   `CONFLICTING` segment that a human must resolve, whatever their recency.
5. If every asserting event was stale the segment is `UNVERIFIED`; if there
   was no asserting event at all it keeps the booked schedule.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.disruption.assessment.freshness import DEFAULT_MAX_EVENT_AGE, is_stale, parse_utc
from app.disruption.contracts import DiscardedEvent, DiscardReason, SegmentStatus, TraceEntry

SOURCE_PRIORITY = {"OPS_CORE": 0, "AIRPORT_FEED": 1, "LEGACY_MIRROR": 2}
TRUSTED_SOURCES = ("OPS_CORE", "AIRPORT_FEED")
_UNKNOWN_PRIORITY = len(SOURCE_PRIORITY)

_STATUS_BY_NAME = {
    "ON_TIME": SegmentStatus.ON_TIME,
    "SCHEDULED": SegmentStatus.SCHEDULED,
    "DELAYED": SegmentStatus.DELAYED,
    "CANCELLED": SegmentStatus.CANCELLED,
}
_QUIET = {SegmentStatus.SCHEDULED, SegmentStatus.ON_TIME}


@dataclass
class SegmentResolution:
    status: SegmentStatus
    delay_minutes: int = 0
    discarded: list[DiscardedEvent] = field(default_factory=list)
    informational: list[str] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)


def _priority(source: str) -> int:
    return SOURCE_PRIORITY.get(source, _UNKNOWN_PRIORITY)


def asserted_state(event: dict[str, Any]) -> tuple[SegmentStatus, int] | None:
    """The status an event asserts, or None if it only carries information."""
    kind = event.get("type")
    if kind == "DELAY":
        return SegmentStatus.DELAYED, int(event.get("delay_minutes") or 0)
    if kind == "CANCELLATION":
        return SegmentStatus.CANCELLED, 0
    if kind == "STATUS":
        status = _STATUS_BY_NAME.get(str(event.get("status")))
        if status is None:
            return None
        return status, int(event.get("delay_minutes") or 0) if status is SegmentStatus.DELAYED else 0
    return None


def compatible(a: SegmentStatus, b: SegmentStatus) -> bool:
    if a in _QUIET and b in _QUIET:
        return True
    return a == b


def reconcile_segment(
    segment_id: str,
    events: list[dict[str, Any]],
    *,
    degraded_sources: set[str],
    retrieved_at: datetime,
    max_age: timedelta = DEFAULT_MAX_EVENT_AGE,
) -> SegmentResolution:
    result = SegmentResolution(status=SegmentStatus.SCHEDULED)
    usable: list[dict[str, Any]] = []
    stale_asserting = 0

    for event in events:
        event_id = event["event_id"]
        if event["source"] in degraded_sources:
            result.discarded.append(
                DiscardedEvent(event_id, DiscardReason.DEGRADED_SOURCE, f"{event['source']} is degraded")
            )
            continue
        if is_stale(parse_utc(event["recorded_at"]), retrieved_at, max_age):
            result.discarded.append(
                DiscardedEvent(event_id, DiscardReason.STALE, f"older than {max_age} at retrieval")
            )
            if asserted_state(event) is not None:
                stale_asserting += 1
            continue
        usable.append(event)

    asserting = [e for e in usable if asserted_state(e) is not None]
    result.informational = [
        f"{e['type']}:{segment_id}" for e in usable if asserted_state(e) is None
    ]

    if not asserting:
        if stale_asserting:
            result.status = SegmentStatus.UNVERIFIED
            note = "only stale events available"
        else:
            note = "no asserting events, booked schedule kept"
        result.trace.append(TraceEntry("reconcile", f"{segment_id}: {note}", {"segment": segment_id}))
        _trace_discards(result, segment_id)
        return result

    latest_by_source: dict[str, dict[str, Any]] = {}
    for event in sorted(asserting, key=lambda e: parse_utc(e["recorded_at"])):
        previous = latest_by_source.get(event["source"])
        if previous is not None:
            result.discarded.append(
                DiscardedEvent(
                    previous["event_id"],
                    DiscardReason.SUPERSEDED_BY_NEWER_EVENT,
                    f"replaced by {event['event_id']}",
                )
            )
        latest_by_source[event["source"]] = event

    trusted = [latest_by_source[s] for s in TRUSTED_SOURCES if s in latest_by_source]
    if len(trusted) == 2 and not compatible(asserted_state(trusted[0])[0], asserted_state(trusted[1])[0]):
        result.status = SegmentStatus.CONFLICTING
        result.trace.append(
            TraceEntry(
                "reconcile",
                f"{segment_id}: trusted sources disagree",
                {"segment": segment_id, "events": [e["event_id"] for e in trusted]},
            )
        )
        _trace_discards(result, segment_id)
        return result

    ranked = sorted(latest_by_source.values(), key=lambda e: _priority(e["source"]))
    winner = ranked[0]
    status, delay = asserted_state(winner)
    for loser in ranked[1:]:
        if not compatible(status, asserted_state(loser)[0]):
            result.discarded.append(
                DiscardedEvent(
                    loser["event_id"],
                    DiscardReason.SUPERSEDED_BY_HIGHER_PRIORITY,
                    f"{winner['source']} ({winner['event_id']}) outranks {loser['source']}",
                )
            )

    result.status, result.delay_minutes = status, delay
    result.trace.append(
        TraceEntry(
            "reconcile",
            f"{segment_id}: {status.value} from {winner['source']} ({winner['event_id']})",
            {"segment": segment_id, "event": winner["event_id"], "delay_minutes": delay},
        )
    )
    _trace_discards(result, segment_id)
    return result


def _trace_discards(result: SegmentResolution, segment_id: str) -> None:
    if result.discarded:
        result.trace.append(
            TraceEntry(
                "discarded_events",
                f"{segment_id}: excluded events",
                {
                    "segment": segment_id,
                    "events": {d.event_id: d.reason.value for d in result.discarded},
                },
            )
        )
