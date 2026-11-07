from dataclasses import replace

import pytest

from app.disruption.actions.service import execute_actions
from app.disruption.actions.write_tools import NOTIFY, MockWriteTools
from app.disruption.communication.messages import DeliveryStatus, build_message, deliver

from .test_actions import decide_for


def message_for(state, *, compensation_requested=False):
    decision = decide_for(state, compensation_requested=compensation_requested)
    actions = execute_actions(decision, state, MockWriteTools())
    return build_message(state, decision, actions)


@pytest.fixture
def abc123_message(abc123_state):
    return message_for(abc123_state)


def test_abc123_message_states_what_happened_and_next_step(abc123_message):
    text = abc123_message.text

    assert "delayed by 160 minutes" in text
    assert "new departure 17:10" in text
    assert "miss your connection NB2410" in text
    assert "NB2412" in text and "2026-09-16" in text and "08:15" in text
    assert "no extra cost" in text
    assert "An agent will contact you to confirm this option" in text
    assert abc123_message.policy_ref == "POL-DELAY-2026-03"
    assert "POL-DELAY-2026-03" in text


def test_abc123_message_hides_internal_and_unverified_data(abc123_message):
    text = abc123_message.text

    for forbidden in ("ON_TIME", "on time", "LEGACY_MIRROR", "OPS_CORE", "E-1012", "NB2450", "O2", "HIGH", "confidence"):
        assert forbidden not in text
    for personal in ("12.345.678-9", "maria.silva@example.com", "8765", "Silva"):
        assert personal not in text
    assert text.startswith("Hello María.")


def test_message_does_not_claim_the_booking_was_changed(abc123_message):
    text = abc123_message.text.lower()

    assert "has been changed" not in text
    assert "rebooked" not in text
    assert "confirmed" not in text


def test_compensation_request_is_neither_promised_nor_denied(abc123_state):
    text = message_for(abc123_state, compensation_requested=True).text

    assert "An agent will review your compensation request." in text
    for claim in ("will be compensated", "approved", "not eligible", "denied", "CLP", "$"):
        assert claim not in text


def test_delivery_is_queued_when_policy_ref_is_present(abc123_message):
    tools = MockWriteTools()

    delivery = deliver(abc123_message, tools)

    assert delivery.status is DeliveryStatus.SENT
    assert delivery.notification_id == "NT-9912"
    [call] = tools.calls_to(NOTIFY)
    assert call.arguments["message"]["policy_ref"] == "POL-DELAY-2026-03"


def test_422_is_recorded_and_not_retried(abc123_message):
    tools = MockWriteTools(notify_statuses=[422])

    delivery = deliver(abc123_message, tools)

    assert delivery.status is DeliveryStatus.BLOCKED
    assert delivery.error == "UNVALIDATED_CONTENT: missing policy_ref"
    assert len(tools.calls_to(NOTIFY)) == 1
    assert "not retried" in delivery.trace[0].message


def test_message_without_policy_ref_is_never_sent(abc123_message):
    tools = MockWriteTools()

    delivery = deliver(replace(abc123_message, policy_ref=None), tools)

    assert delivery.status is DeliveryStatus.NOT_SENT
    assert tools.calls_to(NOTIFY) == []
