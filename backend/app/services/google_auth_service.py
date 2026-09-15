import json
import secrets
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.organization import Organization
from app.models.user import User
from app.services.auth_service import create_authenticated_session


class GoogleAuthNotConfigured(ValueError):
    pass


class GoogleAuthError(ValueError):
    pass


def _settings_or_raise() -> tuple[str, str]:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise GoogleAuthNotConfigured
    return settings.google_client_id, settings.google_client_secret


def create_google_state() -> str:
    settings = get_settings()
    payload = {
        "purpose": "google_oauth",
        "nonce": secrets.token_urlsafe(24),
        "exp": datetime.now(UTC) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def validate_google_state(state: str) -> bool:
    try:
        payload = jwt.decode(state, get_settings().secret_key, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return False
    return payload.get("purpose") == "google_oauth" and isinstance(payload.get("nonce"), str)


def google_authorization_url() -> str:
    client_id, _ = _settings_or_raise()
    settings = get_settings()
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "state": create_google_state(),
            "prompt": "select_account",
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def _post_form(url: str, values: dict[str, str]) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(values).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            parsed = json.loads(response.read().decode("utf-8"))
            if not isinstance(parsed, dict):
                raise GoogleAuthError
            return {str(key): value for key, value in parsed.items()}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise GoogleAuthError from exc


def _get_json(url: str, access_token: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            parsed = json.loads(response.read().decode("utf-8"))
            if not isinstance(parsed, dict):
                raise GoogleAuthError
            return {str(key): value for key, value in parsed.items()}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise GoogleAuthError from exc


def authenticate_google_callback(db: Session, code: str) -> str:
    client_id, client_secret = _settings_or_raise()
    settings = get_settings()
    token_data = _post_form(
        "https://oauth2.googleapis.com/token",
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    access_token = token_data.get("access_token")
    if not isinstance(access_token, str):
        raise GoogleAuthError
    identity = _get_json("https://openidconnect.googleapis.com/v1/userinfo", access_token)
    subject = identity.get("sub")
    email = identity.get("email")
    verified = identity.get("email_verified") is True
    name = identity.get("name")
    if not isinstance(subject, str) or not isinstance(email, str) or not verified:
        raise GoogleAuthError

    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.google_subject == subject))
    if user is None:
        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is not None and user.google_subject not in (None, subject):
            raise GoogleAuthError
    if user is None:
        organization_id = uuid.uuid4()
        organization = Organization(
            id=organization_id,
            name=f"{name if isinstance(name, str) and name.strip() else normalized_email}'s Organization",
            slug=f"org-{organization_id.hex}",
        )
        user = User(
            organization=organization,
            email=normalized_email,
            name=name.strip() if isinstance(name, str) and name.strip() else normalized_email,
            password_hash=None,
            google_subject=subject,
            email_verified_at=datetime.now(UTC),
            is_active=True,
        )
        db.add(user)
    elif not user.is_active:
        raise GoogleAuthError
    else:
        user.google_subject = subject
        user.email_verified_at = user.email_verified_at or datetime.now(UTC)
    try:
        db.flush()
        return create_authenticated_session(db, user)
    except IntegrityError as exc:
        db.rollback()
        raise GoogleAuthError from exc
