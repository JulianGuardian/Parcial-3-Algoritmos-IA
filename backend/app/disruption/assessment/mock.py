"""Minimal, mock-data-backed trip assessment.

NOTE: this is a deliberately simplified stand-in for the full assessment
layer (tasks 2.1-2.6: source reconciliation, freshness, missed-connection
detection, relevance, missing fields). It reads the fixtures directly and
applies just enough logic (priority + degraded-source exclusion, naive
delay propagation, a fixed 60-minute MCT) to produce a real `TripState` for
`ABC123`, so the intake/agents work (4.x, 6.x) has genuine data to operate
on instead of hand-rolled fixtures. It is NOT the task-2 implementation and
must be replaced/reconciled once tasks 2.1-2.6 are done.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from app.disruption.contracts import SegmentState, TraceEntry, TripState

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

_SOURCE_PRIORITY = {"OPS_CORE": 0, "AIRPORT_FEED": 1, "LEGACY_MIRROR": 2}


def _load(name: str) -> dict:
    with (FIXTURES_DIR / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def get_trip_context(booking_id: str) -> dict:
    if booking_id != "ABC123":
        raise LookupError(f"unknown booking_id: {booking_id}")
    return _load("get_trip_context_ABC123.json")


def get_operational_events(booking_id: str) -> dict:
    if booking_id != "ABC123":
        raise LookupError(f"unknown booking_id: {booking_id}")
    return _load("get_operational_events_S1_S2.json")


def _strip_pii(trip: dict) -> None:
    trip.pop("passengers", None)


def assess_trip(booking_id: str, mct_minutes: int = 60) -> TripState:
    trip = get_trip_context(booking_id)
    events = get_operational_events(booking_id)
    degraded = set(events["_meta"]["sources_degraded"])

    passengers = trip["passengers"]
    party_size = len(passengers)
    has_minor = any(p.get("type") == "CHILD" for p in passengers)
    _strip_pii(trip)

    discarded: list[str] = []
    by_segment: dict[str, list[dict]] = {}
    for ev in events["events"]:
        if ev["source"] in degraded:
            discarded.append(ev["event_id"])
            continue
        by_segment.setdefault(ev["segment_id"], []).append(ev)

    segments_by_id = {s["segment_id"]: s for s in trip["segments"]}
    segment_states: list[SegmentState] = []
    arrivals: dict[str, datetime] = {}

    for seg in trip["segments"]:
        sid = seg["segment_id"]
        seg_events = sorted(
            by_segment.get(sid, []),
            key=lambda e: _SOURCE_PRIORITY.get(e["source"], 99),
        )
        delay_minutes = 0
        status = "ON_TIME"
        for ev in seg_events:
            if ev["type"] == "DELAY":
                delay_minutes = max(delay_minutes, ev.get("delay_minutes", 0))
                status = "DELAYED"

        date = seg["date"]
        sched_arrival = datetime.fromisoformat(f"{date}T{seg['scheduled_arrival']}")
        est_arrival = sched_arrival + timedelta(minutes=delay_minutes)
        arrivals[sid] = est_arrival

        segment_states.append(
            SegmentState(
                segment_id=sid,
                flight_number=seg["flight_number"],
                status=status,
                delay_minutes=delay_minutes,
                estimated_arrival=est_arrival.isoformat(),
                missed_connection=False,
            )
        )

    # Missed-connection detection: segment N+1 is missed if the estimated
    # arrival of segment N leaves less than `mct_minutes` before segment
    # N+1's scheduled departure.
    for i in range(len(trip["segments"]) - 1):
        cur = trip["segments"][i]
        nxt = trip["segments"][i + 1]
        cur_arrival = arrivals[cur["segment_id"]]
        next_departure = datetime.fromisoformat(f"{nxt['date']}T{nxt['scheduled_departure']}")
        if (next_departure - cur_arrival) < timedelta(minutes=mct_minutes):
            segment_states[i + 1].missed_connection = True

    missing_fields = list(trip.get("fare_conditions", {}).get("change_penalty_amount", []) or [])
    if trip.get("_meta", {}).get("completeness") == "PARTIAL":
        missing_fields = trip["_meta"].get("missing_fields", [])

    missed_any = any(s.missed_connection for s in segment_states)
    delayed_any = any(s.delay_minutes > 0 for s in segment_states)
    relevant = missed_any or delayed_any

    trace = [
        TraceEntry(
            step="assessment",
            detail={
                "discarded_events": discarded,
                "degraded_sources": sorted(degraded),
            },
        )
    ]

    return TripState(
        booking_id=booking_id,
        party_size=party_size,
        has_minor=has_minor,
        segments=segment_states,
        assessment_status="OK",
        relevant=relevant,
        discarded_events=discarded,
        missing_fields=missing_fields,
        trace=trace,
    )
