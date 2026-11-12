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


def test_cors_aceita_origem_configurada(monkeypatch):
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("CORS_ORIGINS", "https://teste.vercel.app")
    from app.main import create_app
    local = TestClient(create_app())
    response = local.get("/api/health", headers={"Origin": "https://teste.vercel.app"})
    assert response.headers.get("access-control-allow-origin") == "https://teste.vercel.app"
    get_settings.cache_clear()
