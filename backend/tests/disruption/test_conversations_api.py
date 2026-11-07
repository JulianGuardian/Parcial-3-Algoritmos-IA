"""Tests for the conversation API (tasks 4.1, 4.2). No real model call: a
fake ADK model is injected in place of `run_turn`'s production model."""

import json
from functools import partial

import pytest

from app.disruption.agents import conversation_store as store_module
from app.disruption.agents.conversation_store import ConversationStore
from app.disruption.agents.workflow import run_turn as real_run_turn
from tests.disruption.agent_helpers import FakeLlm, call_response, text_response

START_URL = "/api/v1/conversations"


def _intake(**overrides) -> str:
    payload = {"intents": ["TRIP_STATUS"], "compensation_requested": False, "wants_same_day": False, "confidence": 0.9}
    payload.update(overrides)
    return json.dumps(payload)


@pytest.fixture(autouse=True)
def fresh_conversation_store():
    """Each test gets its own in-memory store (it's a process-wide singleton)."""
    store_module.set_conversation_store(ConversationStore())
    yield
    store_module.set_conversation_store(None)


def _use_fake_model(monkeypatch, model):
    """Pin `conversations.run_turn` to always use the given scripted model,
    so the HTTP layer is exercised without any real model call."""
    import app.api.v1.conversations as conversations_module

    monkeypatch.setattr(conversations_module, "run_turn", partial(real_run_turn, model=model))


def test_start_conversation_returns_201_and_an_id(client):
    response = client.post(START_URL, json={"booking_id": "ABC123"})

    assert response.status_code == 201
    body = response.json()
    assert body["booking_id"] == "ABC123"
    assert body["conversation_id"]


def test_start_conversation_unknown_booking_returns_404(client):
    response = client.post(START_URL, json={"booking_id": "ZZZ999"})

    assert response.status_code == 404
    assert response.json()["error"] == "BOOKING_NOT_FOUND"


def test_message_to_unknown_conversation_returns_404(client):
    response = client.post(f"{START_URL}/does-not-exist/messages", json={"message": "hi"})

    assert response.status_code == 404
    assert response.json()["error"] == "CONVERSATION_NOT_FOUND"


def test_message_too_long_returns_422(client):
    conversation_id = client.post(START_URL, json={"booking_id": "ABC123"}).json()["conversation_id"]

    response = client.post(f"{START_URL}/{conversation_id}/messages", json={"message": "x" * 501})

    assert response.status_code == 422


def test_two_turn_abc123_conversation_confirming_o1_opens_a_human_case_without_rebooking(client, monkeypatch):
    conversation_id = client.post(START_URL, json={"booking_id": "ABC123"}).json()["conversation_id"]

    turn1_model = FakeLlm(
        script=[
            text_response(_intake()),
            call_response("get_entitlements", {}),
            text_response("We can offer NB2412. Would you like to confirm it?"),
        ]
    )
    _use_fake_model(monkeypatch, turn1_model)
    turn1 = client.post(
        f"{START_URL}/{conversation_id}/messages",
        json={"message": "What are my options?", "now": "2026-09-15T11:03:00Z"},
    )
    assert turn1.status_code == 200
    # ABC123 always needs a human (R5, minor in the party), so even before
    # any confirmation the turn already points to an agent, not a booking.
    assert turn1.json()["next_step"] == "AGENT_WILL_CONTACT"
    assert turn1.json()["options"][0]["option_id"] == "O1"

    turn2_model = FakeLlm(
        script=[
            text_response(_intake()),
            call_response("request_rebooking", {"option_id": "O1"}),
            call_response("escalate_to_human", {"reason": "POLICY_REQUIRES_HUMAN"}),
            text_response("An agent will follow up to confirm this with you."),
        ]
    )
    _use_fake_model(monkeypatch, turn2_model)
    turn2 = client.post(
        f"{START_URL}/{conversation_id}/messages",
        json={"message": "Yes, book it", "confirm_option_id": "O1", "now": "2026-09-15T11:03:00Z"},
    )

    assert turn2.status_code == 200
    body = turn2.json()
    assert body["human_required"] is True
    assert body["human_case_id"]
    assert body["rebooking_status"] in (None, "BLOCKED")


def test_free_text_book_o1_without_confirm_option_id_creates_nothing(client, monkeypatch):
    """DEF456 has no R5 (adult only), so without the human-required rule
    masking it, the callback must block on NOT_CONFIRMED alone."""
    conversation_id = client.post(START_URL, json={"booking_id": "DEF456"}).json()["conversation_id"]

    model = FakeLlm(
        script=[
            text_response(_intake()),
            call_response("request_rebooking", {"option_id": "O1"}),
            text_response("An agent will follow up to confirm this with you."),
        ]
    )
    _use_fake_model(monkeypatch, model)

    response = client.post(
        f"{START_URL}/{conversation_id}/messages",
        json={"message": "book O1", "now": "2026-09-15T11:03:00Z"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rebooking_status"] in (None, "BLOCKED")
    assert body["human_case_id"] is None
