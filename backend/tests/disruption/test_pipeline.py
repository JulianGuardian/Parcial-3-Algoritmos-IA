from datetime import datetime, timezone

import pytest

from app.disruption.actions.service import RebookingStatus
from app.disruption.actions.write_tools import HUMAN_CASE, NOTIFY, REBOOKING, MockWriteTools
from app.disruption.communication.messages import DeliveryStatus
from app.disruption.contracts import BookingNotFound, Decision, ResolveRequest
from app.disruption.pipeline import resolve_disruption

NOW = datetime(2026, 9, 15, 11, 3, 0, tzinfo=timezone.utc)


def test_abc123_end_to_end_returns_a_decision():
    tools = MockWriteTools()

    resolution = resolve_disruption(ResolveRequest("ABC123", now=NOW), write_tools=tools)

    assert isinstance(resolution.decision, Decision)
    assert resolution.decision.recommended_option.option_id == "O1"
    assert resolution.decision.requires_human is True
    assert resolution.actions.human_case.case_id == "HC-4471"
    assert resolution.actions.rebooking.status is RebookingStatus.NOT_ATTEMPTED
    assert resolution.delivery.status is DeliveryStatus.SENT
    assert len(tools.calls_to(HUMAN_CASE)) == 1
    assert tools.calls_to(REBOOKING) == []
    assert len(tools.calls_to(NOTIFY)) == 1


def test_trace_covers_every_layer():
    resolution = resolve_disruption(ResolveRequest("ABC123", now=NOW))

    steps = {entry.step for entry in resolution.trace}
    assert {"reconcile", "assessment", "rules", "options", "human_gate", "human_case", "notification"} <= steps


def test_unknown_booking_raises_booking_not_found():
    with pytest.raises(BookingNotFound):
        resolve_disruption(ResolveRequest("ZZZ999", now=NOW))


def test_expired_options_are_never_recommended():
    late = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

    resolution = resolve_disruption(ResolveRequest("ABC123", now=late))

    assert resolution.decision.recommended_option is None
    assert resolution.decision.requires_human is True
