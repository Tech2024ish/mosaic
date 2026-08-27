from datetime import UTC, datetime

from app.models.session import UserSession


def is_session_valid(session: UserSession, now: datetime | None = None) -> bool:
    """Return whether a session is active at the supplied instant."""
    instant = now or datetime.now(UTC)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return session.revoked_at is None and expires_at > instant
