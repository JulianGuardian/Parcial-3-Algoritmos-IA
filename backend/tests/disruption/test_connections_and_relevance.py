from datetime import datetime

from app.disruption.assessment.service import assess_trip
from app.disruption.contracts import AssessmentStatus, SegmentStatus

from .conftest import events_response, make_event


def by_id(state, segment_id):
    return next(s for s in state.segments if s.segment_id == segment_id)


# --- 2.5 missed connection ------------------------------------------------- #
def test_s1_arrives_2035_and_s2_is_missed(abc123_state):
    s1, s2 = abc123_state.segments

    assert s1.estimated_arrival == datetime(2026, 9, 15, 20, 35)
    assert s2.scheduled_departure == datetime(2026, 9, 15, 19, 5)
    assert s2.missed_connection is True
    assert s1.missed_connection is False


def test_no_delay_keeps_the_connection(trip):
    state = assess_trip(trip, events_response([]))

    assert by_id(state, "S2").missed_connection is False


def test_minimum_connection_time_is_configurable(trip):
    events = events_response(
        [make_event("A", "S1", "DELAY", "OPS_CORE", "2026-09-15T10:48:00Z", delay_minutes=20)]
    )
    # S1 arrives 18:15; S2 departs 19:05 -> 50 minutes to connect.
    assert by_id(assess_trip(trip, events), "S2").missed_connection is True  # 50 < 60
    assert by_id(assess_trip(trip, events, min_connection_minutes=45), "S2").missed_connection is False


def test_cancelled_segment_has_no_estimate(trip):
    events = events_response([make_event("A", "S1", "CANCELLATION", "OPS_CORE", "2026-09-15T10:48:00Z")])
    s1 = by_id(assess_trip(trip, events), "S1")

    assert s1.status is SegmentStatus.CANCELLED
    assert s1.estimated_arrival is None


# --- 2.6 relevance and missing fields -------------------------------------- #
def test_missed_connection_is_relevant(abc123_state):
    assert abc123_state.relevant is True
    assert "MISSED_CONNECTION:S2" in abc123_state.relevance_reasons
    assert abc123_state.assessment_status is AssessmentStatus.OK


def test_gate_change_only_is_informational(trip):
    events = events_response([make_event("G", "S1", "GATE_CHANGE", "AIRPORT_FEED", "2026-09-15T10:55:00Z", gate="24")])
    state = assess_trip(trip, events)

    assert state.relevant is False
    assert state.relevance_reasons == []
    assert state.informational_changes == ["GATE_CHANGE:S1"]
    assert state.assessment_status is AssessmentStatus.NO_RELEVANT_CHANGE


def test_any_delay_is_relevant(trip):
    events = events_response([make_event("A", "S1", "DELAY", "OPS_CORE", "2026-09-15T10:48:00Z", delay_minutes=10)])
    state = assess_trip(trip, events)

    assert state.relevant is True
    assert "DELAY:S1" in state.relevance_reasons


def test_cancellation_is_relevant(trip):
    events = events_response([make_event("A", "S1", "CANCELLATION", "OPS_CORE", "2026-09-15T10:48:00Z")])

    assert "CANCELLATION:S1" in assess_trip(trip, events).relevance_reasons


def test_change_penalty_amount_is_listed_as_missing(abc123_state):
    assert abc123_state.missing_fields == ["fare_conditions.change_penalty_amount"]
