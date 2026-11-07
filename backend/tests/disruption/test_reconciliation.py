from datetime import datetime

from app.disruption.assessment.service import assess_trip
from app.disruption.contracts import (
    AssessmentStatus,
    DiscardReason,
    SegmentStatus,
)

from .conftest import events_response, make_event


def segment(state, segment_id):
    return next(s for s in state.segments if s.segment_id == segment_id)


def test_abc123_trusted_delay_wins_and_e1012_is_discarded(abc123_state):
    s1 = segment(abc123_state, "S1")

    assert s1.status is SegmentStatus.DELAYED
    assert s1.delay_minutes == 160
    assert s1.estimated_departure == datetime(2026, 9, 15, 17, 10)
    discarded = {d.event_id: d for d in abc123_state.discarded_events}
    assert discarded["E-1012"].reason is DiscardReason.DEGRADED_SOURCE
    assert "LEGACY_MIRROR" in discarded["E-1012"].detail


def test_priority_beats_non_degraded_legacy(trip):
    events = events_response(
        [
            make_event("A", "S1", "DELAY", "OPS_CORE", "2026-09-15T10:48:00Z", delay_minutes=160),
            make_event("B", "S1", "STATUS", "LEGACY_MIRROR", "2026-09-15T10:50:00Z", status="ON_TIME"),
        ]
    )
    state = assess_trip(trip, events)

    assert segment(state, "S1").status is SegmentStatus.DELAYED
    assert [(d.event_id, d.reason) for d in state.discarded_events] == [
        ("B", DiscardReason.SUPERSEDED_BY_HIGHER_PRIORITY)
    ]


def test_degraded_source_event_ids_are_traced(abc123_state):
    trace = next(t for t in abc123_state.trace if t.step == "discarded_events")
    assert trace.data["events"] == {"E-1012": "DEGRADED_SOURCE"}


def test_trusted_sources_disagree_is_conflicting(trip):
    events = events_response(
        [
            make_event("A", "S1", "CANCELLATION", "OPS_CORE", "2026-09-15T10:00:00Z"),
            make_event("B", "S1", "DELAY", "AIRPORT_FEED", "2026-09-15T10:50:00Z", delay_minutes=90),
        ]
    )
    state = assess_trip(trip, events)

    assert segment(state, "S1").status is SegmentStatus.CONFLICTING
    assert state.assessment_status is AssessmentStatus.CONFLICTING


def test_recency_does_not_settle_trusted_disagreement(trip):
    # OPS_CORE is older here; the newer AIRPORT_FEED must not win silently.
    events = events_response(
        [
            make_event("A", "S1", "DELAY", "OPS_CORE", "2026-09-15T09:30:00Z", delay_minutes=160),
            make_event("B", "S1", "STATUS", "AIRPORT_FEED", "2026-09-15T10:55:00Z", status="ON_TIME"),
        ]
    )
    assert assess_trip(trip, events).assessment_status is AssessmentStatus.CONFLICTING


def test_trusted_sources_that_agree_are_not_a_conflict(trip):
    events = events_response(
        [
            make_event("A", "S1", "DELAY", "OPS_CORE", "2026-09-15T10:48:00Z", delay_minutes=160),
            make_event("B", "S1", "DELAY", "AIRPORT_FEED", "2026-09-15T10:50:00Z", delay_minutes=150),
        ]
    )
    s1 = segment(assess_trip(trip, events), "S1")

    assert s1.status is SegmentStatus.DELAYED
    assert s1.delay_minutes == 160  # higher-priority source wins the value


def test_newer_event_from_same_source_wins(trip):
    events = events_response(
        [
            make_event("old", "S1", "DELAY", "OPS_CORE", "2026-09-15T10:00:00Z", delay_minutes=60),
            make_event("new", "S1", "DELAY", "OPS_CORE", "2026-09-15T10:48:00Z", delay_minutes=160),
        ]
    )
    state = assess_trip(trip, events)

    assert segment(state, "S1").delay_minutes == 160
    assert [(d.event_id, d.reason) for d in state.discarded_events] == [
        ("old", DiscardReason.SUPERSEDED_BY_NEWER_EVENT)
    ]


def test_segment_without_events_keeps_schedule(trip):
    state = assess_trip(trip, events_response([]))

    assert all(s.status is SegmentStatus.SCHEDULED for s in state.segments)
    assert state.assessment_status is AssessmentStatus.NO_RELEVANT_CHANGE
