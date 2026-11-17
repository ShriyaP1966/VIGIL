from fastapi.testclient import TestClient
from backend.app.main import app


def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "offline"
    assert data["version"] == "3.1.0"
    assert "timestamp" in data


def test_request_id_middleware():
    client = TestClient(app)
    response = client.get("/health", headers={"X-Request-ID": "test-req-123"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-req-123"
