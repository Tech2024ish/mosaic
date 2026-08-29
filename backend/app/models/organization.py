from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel


class Organization(TimestampedModel):
    __tablename__ = "organizations"
    __table_args__ = (Index("ix_organizations_slug", "slug", unique=False),)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    users = relationship("User", back_populates="organization")
