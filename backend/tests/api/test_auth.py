import uuid

import pytest
from conftest import verify_test_user
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.auth import create_access_token
from app.infrastructure.database.session import SessionLocal, engine
from app.main import app
from app.models.base import Base
from app.models.organization import Organization
from app.models.user import User
from app.routers import auth as auth_router

Base.metadata.create_all(engine)


def registration_payload() -> dict[str, str]:
    suffix = uuid.uuid4().hex
    return {
        "email": f"owner-{suffix}@example.com",
        "name": "  Amina   Ndlovu ",
        "password": "Secure password 123!",
    }


def test_registration_creates_user_and_tenant_without_hash() -> None:
    payload = registration_payload()
    response = TestClient(app).post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == payload["email"].lower()
    assert body["name"] == "Amina Ndlovu"
    assert "password_hash" not in body
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == payload["email"].lower()))
        assert user is not None
        assert user.organization_id is not None
        assert db.get(Organization, user.organization_id) is not None


def test_duplicate_email_is_rejected_case_insensitively() -> None:
    payload = registration_payload()
    client = TestClient(app)
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    verify_test_user(payload["email"])
    duplicate = {**payload, "email": payload["email"].upper()}
    response = client.post("/api/v1/auth/register", json=duplicate)
    assert response.status_code == 409
    assert "password_hash" not in response.text


def test_login_returns_token_and_rejects_invalid_password() -> None:
    payload = registration_payload()
    client = TestClient(app)
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    verify_test_user(payload["email"])
    response = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"].upper(), "password": payload["password"]},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    invalid = client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": "wrong password"}
    )
    assert invalid.status_code == 401
    assert invalid.json()["detail"] == "Invalid email or password"


def test_unverified_user_cannot_login() -> None:
    payload = registration_payload()
    client = TestClient(app)
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 403
    assert response.json()["detail"] == "Please verify your email before signing in"


def test_email_verification_enables_login_and_is_one_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = registration_payload()
    captured: dict[str, str] = {}

    def capture_email(email: str, name: str, token: str) -> None:
        captured["email"] = email
        captured["token"] = token

    monkeypatch.setattr(auth_router, "send_verification_email", capture_email)
    client = TestClient(app)
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert captured["email"] == payload["email"].lower()

    verification = client.get(
        "/api/v1/auth/verify-email", params={"token": captured["token"]}, follow_redirects=False
    )
    assert verification.status_code == 307
    assert "Email%20verified%20successfully" in verification.headers["location"]
    assert client.post("/api/v1/auth/login", json=payload).status_code == 200

    reused = client.get(
        "/api/v1/auth/verify-email", params={"token": captured["token"]}, follow_redirects=False
    )
    assert "invalid%20or%20expired" in reused.headers["location"]


def test_inactive_user_cannot_login() -> None:
    payload = registration_payload()
    client = TestClient(app)
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == payload["email"].lower()))
        assert user is not None
        user.is_active = False
        db.commit()
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


def test_me_requires_auth_and_returns_safe_user_data() -> None:
    payload = registration_payload()
    client = TestClient(app)
    registered = client.post("/api/v1/auth/register", json=payload).json()
    token = create_access_token(uuid.UUID(registered["id"]))
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == registered["id"]
    assert "password_hash" not in response.json()
    assert client.get("/api/v1/auth/me").status_code == 401
