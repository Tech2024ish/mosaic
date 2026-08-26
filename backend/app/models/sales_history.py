import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel


class SalesHistory(TimestampedModel):
    __tablename__ = "sales_history"
    __table_args__ = (
        Index("ix_sales_history_org_date", "organization_id", "sale_date"),
        Index("ix_sales_history_org_product", "organization_id", "product_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    import_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_jobs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row_number: Mapped[int] = mapped_column(nullable=False)
    product_code: Mapped[str] = mapped_column(String(200), nullable=False)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    warehouse_code: Mapped[str] = mapped_column(String(200), nullable=False)
    row_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    import_job = relationship("ImportJob", back_populates="sales_records")
