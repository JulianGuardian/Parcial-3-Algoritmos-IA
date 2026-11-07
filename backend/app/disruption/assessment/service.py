"""Assessment layer entry point: raw tool responses -> `TripState`."""

from datetime import timedelta
from typing import Any

from app.disruption.assessment.connections import (
    DEFAULT_MIN_CONNECTION_MINUTES,
    apply_estimates,
    schedule,
)
from app.disruption.assessment.freshness import DEFAULT_MAX_EVENT_AGE, parse_utc
from app.disruption.assessment.privacy import strip_passengers
from app.disruption.assessment.reconciliation import reconcile_segment
from app.disruption.assessment.relevance import classify_relevance
from app.disruption.contracts import (
    AssessmentStatus,
    FareConditions,
    SegmentState,
    SegmentStatus,
    TraceEntry,
    TripState,
)


def assess_trip(
    trip_context: dict[str, Any],
    events_response: dict[str, Any],
    *,
    max_event_age: timedelta = DEFAULT_MAX_EVENT_AGE,
    min_connection_minutes: int = DEFAULT_MIN_CONNECTION_MINUTES,
) -> TripState:
    """Build the single verified view of what happened to the trip.

    `max_event_age` and `min_connection_minutes` are the configurable knobs
    (defaults: 2 hours and 60 minutes).
    """
    passengers, has_minor = strip_passengers(trip_context["passengers"])
    fare = trip_context.get("fare_conditions") or {}
    state = TripState(
        booking_id=trip_context["booking_id"],
        party_size=len(passengers),
        has_minor=has_minor,
        passengers=passengers,
        fare_conditions=FareConditions(
            changeable=fare.get("changeable"),
            refundable=fare.get("refundable"),
            fare_family=fare.get("fare_family"),
        ),
    )

    meta = events_response.get("_meta", {})
    retrieved_at = parse_utc(meta["retrieved_at"])
    degraded = set(meta.get("sources_degraded", []))
    events = events_response.get("events", [])

    for raw in trip_context["segments"]:
        departure, arrival = schedule(raw["date"], raw["scheduled_departure"], raw["scheduled_arrival"])
        resolution = reconcile_segment(
            raw["segment_id"],
            [e for e in events if e["segment_id"] == raw["segment_id"]],
            degraded_sources=degraded,
            retrieved_at=retrieved_at,
            max_age=max_event_age,
        )
        state.segments.append(
            SegmentState(
                segment_id=raw["segment_id"],
                flight_number=raw["flight_number"],
                origin=raw["origin"],
                destination=raw["destination"],
                status=resolution.status,
                delay_minutes=resolution.delay_minutes,
                scheduled_departure=departure,
                scheduled_arrival=arrival,
            )
        )
        state.discarded_events.extend(resolution.discarded)
        state.informational_changes.extend(resolution.informational)
        state.trace.extend(resolution.trace)

    apply_estimates(state.segments, min_connection_minutes)
    for segment in state.segments:
        if segment.missed_connection:
            state.trace.append(
                TraceEntry(
                    "missed_connection",
                    f"{segment.segment_id}: departs before previous arrival + {min_connection_minutes} min",
                    {"segment": segment.segment_id},
                )
            )

    state.relevant, state.relevance_reasons = classify_relevance(state.segments)
    state.missing_fields = list(dict.fromkeys(trip_context.get("_meta", {}).get("missing_fields", [])))
    state.assessment_status = _overall_status(state)
    state.trace.append(
        TraceEntry(
            "assessment",
            f"status {state.assessment_status.value}, relevant={state.relevant}",
            {"reasons": state.relevance_reasons, "missing_fields": state.missing_fields},
        )
    )
    return state


def _overall_status(state: TripState) -> AssessmentStatus:
    statuses = {s.status for s in state.segments}
    if SegmentStatus.CONFLICTING in statuses:
        return AssessmentStatus.CONFLICTING
    if SegmentStatus.UNVERIFIED in statuses:
        return AssessmentStatus.UNVERIFIED
    return AssessmentStatus.OK if state.relevant else AssessmentStatus.NO_RELEVANT_CHANGE
