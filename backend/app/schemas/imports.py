import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DatasetType(StrEnum):
    SALES_HISTORY = "sales_history"


class ImportStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


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
    processing_imports: int
    total_rows: int
    successful_rows: int
    failed_rows: int


class RetryResponse(BaseModel):
    import_id: uuid.UUID
    status: ImportStatus
    message: str
