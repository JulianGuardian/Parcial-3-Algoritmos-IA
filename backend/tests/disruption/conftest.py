from copy import deepcopy

import pytest

from app.disruption.assessment.service import assess_trip
from app.disruption.assessment.sources import get_operational_events, get_trip_context


@pytest.fixture
def trip():
    return get_trip_context("ABC123")


@pytest.fixture
def events():
    return get_operational_events(["S1", "S2"])


@pytest.fixture
def abc123_state(trip, events):
    return assess_trip(trip, events)


def make_event(event_id, segment_id, kind, source, recorded_at, **extra):
    return {
        "event_id": event_id,
        "segment_id": segment_id,
        "type": kind,
        "source": source,
        "recorded_at": recorded_at,
        **extra,
    }


def events_response(events, *, retrieved_at="2026-09-15T11:02:33Z", degraded=()):
    return {
        "events": deepcopy(events),
        "_meta": {
            "retrieved_at": retrieved_at,
            "sources_available": ["OPS_CORE", "AIRPORT_FEED", "LEGACY_MIRROR"],
            "sources_degraded": list(degraded),
        },
    }
