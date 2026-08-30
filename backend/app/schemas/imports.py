import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DatasetType(StrEnum):
    SALES_HISTORY = "sales_history"
    PRODUCTS = "products"
    WAREHOUSES = "warehouses"
    SUPPLIERS = "suppliers"
    INVENTORY_SNAPSHOTS = "inventory_snapshots"


class ImportStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_type: DatasetType
    original_filename: str
    status: ImportStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    total_rows: int
    successful_rows: int
    failed_rows: int
    error_summary: dict[str, object] | None


class ImportErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_number: int
    field_name: str | None
    error_code: str
    message: str
    raw_value: str | None


class ImportStatsResponse(BaseModel):
    total_imports: int
    successful_imports: int
    failed_imports: int
    cancelled_imports: int
    retry_count: int
    processing_imports: int
    total_rows: int
    successful_rows: int
    failed_rows: int


class ImportEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    actor_id: uuid.UUID | None
    event_metadata: dict[str, object] | None
    created_at: datetime


class CancelResponse(BaseModel):
    import_id: uuid.UUID
    status: ImportStatus
    message: str


class RetryResponse(BaseModel):
    import_id: uuid.UUID
    status: ImportStatus
    message: str
