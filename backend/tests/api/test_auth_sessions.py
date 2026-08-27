import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.auth import create_access_token
from app.infrastructure.database.session import SessionLocal
from app.main import app
from app.models.session import UserSession
from app.models.user import User


def account() -> dict[str, str]:
    suffix = uuid.uuid4().hex
    return {
        "email": f"session-{suffix}@example.com",
        "name": "Session Owner",
        "password": "Secure password 123!",
    }


def test_login_creates_a_database_session() -> None:
    payload = account()
    client = TestClient(app)
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == payload["email"]))
        assert user is not None
        session = db.scalar(select(UserSession).where(UserSession.user_id == user.id))
        assert session is not None
        assert session.revoked_at is None


def test_logout_revokes_the_current_session() -> None:
    payload = account()
    client = TestClient(app)
    client.post("/api/v1/auth/register", json=payload)
    token = client.post("/api/v1/auth/login", json=payload).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_malformed_and_expired_session_tokens_are_rejected() -> None:
    payload = account()
    client = TestClient(app)
    client.post("/api/v1/auth/register", json=payload)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == payload["email"]))
        assert user is not None
        session = UserSession(user_id=user.id, expires_at=datetime.now(UTC) - timedelta(minutes=1))
        db.add(session)
        db.flush()
        expired_token = create_access_token(
            user.id, session.id, datetime.now(UTC) - timedelta(minutes=1)
        )
        db.commit()

    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
        ).status_code
        == 401
    )


def test_session_cannot_be_used_by_a_different_user() -> None:
    first, second = account(), account()
    client = TestClient(app)
    client.post("/api/v1/auth/register", json=first)
    client.post("/api/v1/auth/register", json=second)
    with SessionLocal() as db:
        first_user = db.scalar(select(User).where(User.email == first["email"]))
        second_user = db.scalar(select(User).where(User.email == second["email"]))
        assert first_user is not None and second_user is not None
        session = UserSession(
            user_id=second_user.id,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        db.add(session)
        db.flush()
        token = create_access_token(first_user.id, session.id, session.expires_at)
        db.commit()

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_missing_login_fields_are_rejected() -> None:
    response = TestClient(app).post("/api/v1/auth/login", json={"email": "x@example.com"})
    assert response.status_code == 422
