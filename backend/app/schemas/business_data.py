import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class SalesHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_code: str
    sale_date: date
    quantity: Decimal
    unit_price: Decimal
    warehouse_code: str
    import_job_id: uuid.UUID
    source_row_number: int
    created_at: datetime


class BusinessQuery(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)
    search: str | None = Field(default=None, max_length=100)
    sort: str = "code"
    order: SortOrder = SortOrder.ASC


class InventoryQuery(BusinessQuery):
    sort: str = "snapshot_date"
    product_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID | None = None
    snapshot_date_from: date | None = None
    snapshot_date_to: date | None = None


class SalesQuery(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)
    product_code: str | None = Field(default=None, max_length=200)
    warehouse_code: str | None = Field(default=None, max_length=200)
    sale_date_from: date | None = None
    sale_date_to: date | None = None
    sort: str = "sale_date"
    order: SortOrder = SortOrder.DESC
