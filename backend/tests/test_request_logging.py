def request_lines(log_lines):
    return [line for line in log_lines() if line["logger"] == "app.request"]


def test_generates_request_id_when_missing(client, log_lines):
    response = client.get("/health")

    request_id = response.headers["X-Request-ID"]
    assert request_id
    (line,) = request_lines(log_lines)
    assert line["request_id"] == request_id
    assert line["method"] == "GET"
    assert line["path"] == "/health"
    assert line["status_code"] == 200
    assert line["duration_ms"] >= 0


def test_reuses_client_request_id(client, log_lines):
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})

    assert response.headers["X-Request-ID"] == "abc-123"
    (line,) = request_lines(log_lines)
    assert line["request_id"] == "abc-123"


def test_replaces_unsafe_client_request_id(client, log_lines):
    response = client.get("/health", headers={"X-Request-ID": "bad id\twith spaces"})

    assert response.headers["X-Request-ID"] != "bad id\twith spaces"
    assert len(response.headers["X-Request-ID"]) == 32


def test_query_string_is_not_logged(client, log_lines):
    client.get("/health?passport=X1234567")

    (line,) = request_lines(log_lines)
    assert line["path"] == "/health"
    assert "X1234567" not in str(line)
