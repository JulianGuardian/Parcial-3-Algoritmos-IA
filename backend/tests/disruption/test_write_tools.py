import pytest

from app.disruption.actions.write_tools import (
    HUMAN_CASE,
    NOTIFY,
    REBOOKING,
    MockWriteTools,
)

OPTION_O1 = {"option_id": "O1", "flight_number": "NB2412"}
VALID_MESSAGE = {"text": "Your connection was missed.", "policy_ref": "POL-DELAY-2026-03"}


def test_rebooking_defaults_to_pending_confirmation():
    tools = MockWriteTools()

    response = tools.create_rebooking_request(OPTION_O1, idempotency_key="k-1")

    assert response.status_code == 201
    assert response.ok
    assert response.body == {
        "request_id": "RBK-88231",
        "status": "PENDING_CONFIRMATION",
        "expires_at": "2026-09-15T11:12:00Z",
    }


def test_rebooking_duplicate_returns_existing_request_id():
    tools = MockWriteTools(rebooking_statuses=[409])

    response = tools.create_rebooking_request(OPTION_O1, idempotency_key="k-1")

    assert response.status_code == 409
    assert not response.ok
    assert response.body == {"error": "DUPLICATE_REQUEST", "request_id": "RBK-88231"}


def test_rebooking_timeouts_are_consumed_in_order_then_succeed():
    tools = MockWriteTools(rebooking_statuses=[503, 503])

    statuses = [
        tools.create_rebooking_request(OPTION_O1, idempotency_key="k-1").status_code
        for _ in range(3)
    ]

    assert statuses == [503, 503, 201]
    assert tools.calls_to(REBOOKING)[0].response.body == {"error": "UPSTREAM_TIMEOUT"}


def test_rebooking_calls_record_option_and_idempotency_key():
    tools = MockWriteTools()

    tools.create_rebooking_request(OPTION_O1, idempotency_key="k-1")

    [call] = tools.calls_to(REBOOKING)
    assert call.arguments == {"option": OPTION_O1, "idempotency_key": "k-1"}


def test_human_case_returns_case_and_queue():
    tools = MockWriteTools()

    response = tools.create_human_case("R5_PRIORITY_HANDLING", {"booking_id": "ABC123"})

    assert response.status_code == 201
    assert response.body == {"case_id": "HC-4471", "queue": "DISRUPTION_L2", "sla_minutes": 45}
    assert tools.calls_to(HUMAN_CASE)[0].arguments["reason"] == "R5_PRIORITY_HANDLING"


def test_notify_with_policy_ref_is_queued():
    tools = MockWriteTools()

    response = tools.notify_passenger(VALID_MESSAGE)

    assert response.status_code == 202
    assert response.body == {"notification_id": "NT-9912", "channel": "PUSH", "status": "QUEUED"}


def test_notify_without_policy_ref_is_rejected():
    tools = MockWriteTools()

    response = tools.notify_passenger({"text": "Your connection was missed."})

    assert response.status_code == 422
    assert response.body == {"error": "UNVALIDATED_CONTENT", "detail": "missing policy_ref"}


def test_notify_rejection_can_be_injected():
    tools = MockWriteTools(notify_statuses=[422])

    assert tools.notify_passenger(VALID_MESSAGE).status_code == 422
    assert tools.notify_passenger(VALID_MESSAGE).status_code == 202


def test_unknown_status_is_rejected_at_construction():
    with pytest.raises(ValueError, match="no fixture for status"):
        MockWriteTools(human_case_statuses=[503])


def test_responses_are_independent_copies():
    tools = MockWriteTools()

    first = tools.notify_passenger(VALID_MESSAGE)
    first.body["status"] = "TAMPERED"

    assert tools.notify_passenger(VALID_MESSAGE).body["status"] == "QUEUED"
    assert len(tools.calls_to(NOTIFY)) == 2
