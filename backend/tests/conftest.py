import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from datetime import UTC, datetime

from sqlalchemy import select

from app.infrastructure.database.session import SessionLocal
from app.models.user import User


def verify_test_user(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.email_verified_at = datetime.now(UTC)
        db.commit()
