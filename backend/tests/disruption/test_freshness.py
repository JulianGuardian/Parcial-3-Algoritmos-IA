from datetime import timedelta

from app.disruption.assessment.freshness import is_stale, parse_utc
from app.disruption.assessment.service import assess_trip
from app.disruption.contracts import AssessmentStatus, DiscardReason, SegmentStatus

from .conftest import events_response, make_event

RETRIEVED = parse_utc("2026-09-15T11:02:33Z")


def test_e1001_is_fresh(abc123_state):
    assert "E-1001" not in {d.event_id for d in abc123_state.discarded_events}
    s1 = next(s for s in abc123_state.segments if s.segment_id == "S1")
    assert s1.status is SegmentStatus.DELAYED


def test_age_boundary_is_strict():
    two_hours_ago = RETRIEVED - timedelta(hours=2)
    assert is_stale(two_hours_ago, RETRIEVED) is False
    assert is_stale(two_hours_ago - timedelta(seconds=1), RETRIEVED) is True


def test_max_age_is_configurable():
    ten_minutes_ago = RETRIEVED - timedelta(minutes=10)
    assert is_stale(ten_minutes_ago, RETRIEVED, timedelta(minutes=5)) is True
    assert is_stale(ten_minutes_ago, RETRIEVED, timedelta(minutes=30)) is False


def test_only_a_stale_event_makes_s1_unverified(trip):
    events = events_response(
        [make_event("OLD", "S1", "DELAY", "OPS_CORE", "2026-09-15T07:00:00Z", delay_minutes=160)]
    )
    state = assess_trip(trip, events)

    s1 = next(s for s in state.segments if s.segment_id == "S1")
    assert s1.status is SegmentStatus.UNVERIFIED
    assert s1.delay_minutes == 0
    assert s1.estimated_arrival is None
    assert state.assessment_status is AssessmentStatus.UNVERIFIED
    assert [(d.event_id, d.reason) for d in state.discarded_events] == [("OLD", DiscardReason.STALE)]
    assert any(t.step == "discarded_events" and "OLD" in t.data["events"] for t in state.trace)


def test_unverified_segment_never_produces_a_missed_connection(trip):
    events = events_response(
        [make_event("OLD", "S1", "DELAY", "OPS_CORE", "2026-09-15T07:00:00Z", delay_minutes=160)]
    )
    state = assess_trip(trip, events)

    assert not any(s.missed_connection for s in state.segments)


def test_stale_event_does_not_override_a_fresh_one(trip):
    events = events_response(
        [
            make_event("OLD", "S1", "STATUS", "OPS_CORE", "2026-09-15T07:00:00Z", status="ON_TIME"),
            make_event("NEW", "S1", "DELAY", "OPS_CORE", "2026-09-15T10:48:00Z", delay_minutes=160),
        ]
    )
    state = assess_trip(trip, events)

    assert next(s for s in state.segments if s.segment_id == "S1").status is SegmentStatus.DELAYED
