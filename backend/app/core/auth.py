import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.auth.session_policy import is_session_valid
from app.infrastructure.database.session import get_db
from app.models.session import UserSession
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(
    user_id: uuid.UUID,
    session_id: uuid.UUID | None = None,
    expires_at: datetime | None = None,
) -> str:
    settings = get_settings()
    expires = expires_at or (
        datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, str | datetime] = {"sub": str(user_id), "exp": expires}
    if session_id is not None:
        payload["sid"] = str(session_id)
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _get_authentication(
    credentials: HTTPAuthorizationCredentials | None, db: Session, require_session: bool = False
) -> tuple[User, UserSession | None]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        payload = jwt.decode(
            credentials.credentials, get_settings().secret_key, algorithms=["HS256"]
        )
        user_id = uuid.UUID(payload["sub"])
        session_id = uuid.UUID(payload["sid"]) if "sid" in payload else None
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token"
        ) from exc
    if require_session and session_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token"
        )
    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token"
        )
    session = None
    if session_id is not None:
        session = db.scalar(
            select(UserSession).where(UserSession.id == session_id, UserSession.user_id == user_id)
        )
        if session is None or not is_session_valid(session):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token"
            )
    return user, session


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    user, _ = _get_authentication(credentials, db)
    return user


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserSession:
    _, session = _get_authentication(credentials, db, require_session=True)
    assert session is not None
    return session
