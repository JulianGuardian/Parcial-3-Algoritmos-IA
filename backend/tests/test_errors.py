from fastapi.testclient import TestClient


def test_unhandled_error_returns_generic_500(app, log_lines):
    @app.get("/boom")
    def boom():
        raise RuntimeError("secret-internal-detail")

    client = TestClient(app)
    response = client.get("/boom", headers={"X-Request-ID": "req-500"})

    assert response.status_code == 500
    body = response.json()
    assert body == {"detail": "Internal server error", "request_id": "req-500"}
    assert "secret-internal-detail" not in response.text
    assert "Traceback" not in response.text
    assert response.headers["X-Request-ID"] == "req-500"

    lines = log_lines()
    error = next(line for line in lines if line["message"] == "unhandled error")
    assert error["request_id"] == "req-500"
    assert "secret-internal-detail" in error["exception"]
    request = next(line for line in lines if line["message"] == "request")
    assert request["status_code"] == 500
