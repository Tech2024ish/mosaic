import uuid

from sqlalchemy import JSON, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel


class ImportEvent(TimestampedModel):
    __tablename__ = "import_events"
    __table_args__ = (
        Index("ix_import_events_org_created", "organization_id", "created_at"),
        Index("ix_import_events_import_created", "import_job_id", "created_at"),
    )

    import_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    event_metadata: Mapped[dict[str, object] | None] = mapped_column("metadata", JSON)

    import_job = relationship("ImportJob", back_populates="events")
    actor = relationship("User")
