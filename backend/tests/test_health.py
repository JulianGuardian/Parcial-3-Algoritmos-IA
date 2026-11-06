def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_are_served_outside_the_api_prefix(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_unversioned_business_route_is_404(client, app):
    @app.get("/api/v1/ping")
    def ping():
        return {"pong": True}

    assert client.get("/api/v1/ping").status_code == 200
    assert client.get("/ping").status_code == 404
