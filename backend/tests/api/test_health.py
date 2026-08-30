import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import health


def test_api_root() -> None:
    client = TestClient(app)
    response = client.get("/api/v1")
    assert response.status_code == 200
    assert response.json() == {"name": "MOSAIC API", "version": "v1"}


def test_health_reports_database_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "check_database_connection", lambda: True)
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
