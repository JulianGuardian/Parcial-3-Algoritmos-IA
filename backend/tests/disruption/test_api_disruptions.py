from app.disruption import pipeline
from app.disruption.contracts import ToolUnavailable

URL = "/api/v1/disruptions/{}/resolve"
NOW = "2026-09-15T11:03:00Z"


def resolve(client, booking_id="ABC123", **body):
    return client.post(URL.format(booking_id), json={"now": NOW, **body}, headers={"X-Request-ID": "req-test"})


def test_abc123_returns_200_with_human_required_and_no_personal_data(client):
    response = resolve(client)

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req-test"
    assert body["decision"]["requires_human"] is True
    assert body["decision"]["human_reasons"] == ["R5_PRIORITY_HANDLING"]
    assert body["decision"]["recommended_option"]["option_id"] == "O1"
    assert body["decision"]["policy_ref"] == "POL-DELAY-2026-03"
    assert body["actions"]["human_case"]["case_id"] == "HC-4471"
    assert body["actions"]["rebooking"]["status"] == "NOT_ATTEMPTED"
    assert body["notification"]["status"] == "SENT"
    assert body["assessment"]["segments"][1]["missed_connection"] is True

    for personal in ("document_id", "12.345.678-9", "maria.silva@example.com", "8765 4321", "Silva"):
        assert personal not in response.text


def test_body_is_optional(client):
    response = client.post(URL.format("ABC123"))

    assert response.status_code == 200


def test_compensation_request_adds_r4_to_a_single_case(client):
    body = resolve(client, compensation_requested=True).json()

    assert set(body["actions"]["human_case"]["reasons"]) == {"R4_CASH_COMPENSATION", "R5_PRIORITY_HANDLING"}
    assert "An agent will review your compensation request." in body["notification"]["text"]


def test_unknown_booking_is_404(client):
    response = resolve(client, booking_id="ZZZ999")

    assert response.status_code == 404
    assert response.json() == {
        "error": "BOOKING_NOT_FOUND",
        "detail": "No booking matches this id.",
        "request_id": "req-test",
    }


def test_invalid_input_is_422(client):
    response = resolve(client, question="x" * 501)

    assert response.status_code == 422


def test_read_tool_failure_is_503_without_internals(client, monkeypatch):
    def broken(segment_ids):
        raise ToolUnavailable("get_operational_events: OPS_CORE connection refused")

    monkeypatch.setattr(pipeline, "get_operational_events", broken)

    response = resolve(client)

    assert response.status_code == 503
    assert response.json()["error"] == "UPSTREAM_UNAVAILABLE"
    assert response.json()["request_id"] == "req-test"
    for leaked in ("OPS_CORE", "connection refused", "get_operational_events", "Traceback"):
        assert leaked not in response.text
