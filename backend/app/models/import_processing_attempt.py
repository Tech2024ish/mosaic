import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel


class ImportProcessingAttempt(TimestampedModel):
    __tablename__ = "import_processing_attempts"
    __table_args__ = (
        Index("ix_import_attempts_org_import", "organization_id", "import_job_id"),
        Index("ix_import_attempts_import_started", "import_job_id", "started_at"),
    )

    import_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    failure_category: Mapped[str | None] = mapped_column(String(50))
    duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    import_job = relationship("ImportJob", back_populates="processing_attempts")
    organization = relationship("Organization")
