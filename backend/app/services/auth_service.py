import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import create_access_token
from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.email_verification_token import EmailVerificationToken
from app.models.organization import Organization
from app.models.password_reset_token import PasswordResetToken
from app.models.session import UserSession
from app.models.user import User


class DuplicateEmailError(ValueError):
    pass


class UnverifiedEmailError(ValueError):
    pass


def register_user(db: Session, email: str, name: str, password: str) -> tuple[User, str]:
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
        email_verified_at=None,
    )
    db.add(user)
    try:
        db.flush()
        raw_token = secrets.token_urlsafe(32)
        db.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                expires_at=datetime.now(UTC)
                + timedelta(minutes=get_settings().email_verification_expire_minutes),
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEmailError from exc
    db.refresh(user)
    return user, raw_token


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not user.is_active or user.password_hash is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if user.email_verified_at is None:
        raise UnverifiedEmailError
    return user


def verify_email(db: Session, raw_token: str) -> User | None:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = db.scalar(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
    )
    now = datetime.now(UTC)
    expires_at = (
        token.expires_at.replace(tzinfo=UTC)
        if token and token.expires_at.tzinfo is None
        else token.expires_at
        if token
        else None
    )
    if token is None or token.used_at is not None or expires_at is None or expires_at <= now:
        return None
    user = db.get(User, token.user_id)
    if user is None:
        return None
    user.email_verified_at = now
    token.used_at = now
    db.commit()
    return user


def create_password_reset(db: Session, email: str) -> tuple[User, str] | None:
    user = db.scalar(
        select(User).where(User.email == email.strip().lower(), User.is_active.is_(True))
    )
    if user is None or user.password_hash is None or user.email_verified_at is None:
        return None
    now = datetime.now(UTC)
    for token in user.password_reset_tokens:
        if token.used_at is None:
            token.used_at = now
    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=now + timedelta(minutes=get_settings().password_reset_expire_minutes),
        )
    )
    db.commit()
    return user, raw_token


def reset_password(db: Session, raw_token: str, new_password: str) -> bool:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    now = datetime.now(UTC)
    expires_at = (
        token.expires_at.replace(tzinfo=UTC)
        if token and token.expires_at.tzinfo is None
        else token.expires_at
        if token
        else None
    )
    if token is None or token.used_at is not None or expires_at is None or expires_at <= now:
        return False
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        return False
    user.password_hash = hash_password(new_password)
    token.used_at = now
    for session in user.sessions:
        if session.revoked_at is None:
            session.revoked_at = now
    db.commit()
    return True


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
