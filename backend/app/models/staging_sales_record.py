import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Date, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel


class StagingSalesRecord(TimestampedModel):
    __tablename__ = "staging_sales_records"

    import_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number: Mapped[int] = mapped_column(nullable=False)
    raw_payload: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(200))
    sale_date: Mapped[date | None] = mapped_column(Date)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    warehouse_code: Mapped[str | None] = mapped_column(String(200))
    is_valid: Mapped[bool] = mapped_column(nullable=False, default=False)
    import_job = relationship("ImportJob", back_populates="staging_records")
