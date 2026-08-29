from enum import StrEnum


class ImportEventType(StrEnum):
    CREATED = "created"
    PROCESSING_STARTED = "processing_started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY_REQUESTED = "retry_requested"
