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


def test_request_id_is_generated_and_propagated() -> None:
    response = TestClient(app).get("/api/v1")
    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_safe_request_id_is_propagated_and_invalid_values_are_replaced() -> None:
    client = TestClient(app)
    supplied = client.get("/api/v1", headers={"X-Request-ID": "ops-2026-01"})
    assert supplied.headers["X-Request-ID"] == "ops-2026-01"
    invalid = client.get("/api/v1", headers={"X-Request-ID": "x" * 129})
    assert invalid.headers["X-Request-ID"] != "x" * 129
    assert len(invalid.headers["X-Request-ID"]) == 36


def test_readiness_reports_database_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "check_database_connection", lambda: True)
    response = TestClient(app).get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}
