from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_responde_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["horizon_pregoes"] == 14
    assert len(body["ativos"]) == 8
