import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import create_access_token
from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.organization import Organization
from app.models.session import UserSession
from app.models.user import User


class DuplicateEmailError(ValueError):
    pass


def register_user(db: Session, email: str, name: str, password: str) -> User:
    normalized_email = email.strip().lower()
    if db.scalar(select(User.id).where(User.email == normalized_email)) is not None:
        raise DuplicateEmailError
    organization_id = uuid.uuid4()
    organization = Organization(
        id=organization_id,
        name=f"{name}'s Organization",
        slug=f"org-{organization_id.hex}",
    )
    user = User(
        organization=organization,
        email=normalized_email,
        name=name,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEmailError from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user


def issue_token(user: User) -> str:
    return create_access_token(user.id)


def create_authenticated_session(db: Session, user: User) -> str:
    """Create a database-backed session and issue its matching bearer token."""
    expires_at = datetime.now(UTC) + timedelta(minutes=get_settings().access_token_expire_minutes)
    session = UserSession(user_id=user.id, expires_at=expires_at)
    db.add(session)
    db.flush()
    token = create_access_token(user.id, session.id, expires_at)
    db.commit()
    return token


def revoke_session(db: Session, session: UserSession) -> None:
    session.revoked_at = datetime.now(UTC)
    db.commit()
