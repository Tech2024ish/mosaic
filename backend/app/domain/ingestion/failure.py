from enum import StrEnum


class FailureCategory(StrEnum):
    VALIDATION_ERROR = "validation_error"
    STORAGE_ERROR = "storage_error"
    DATABASE_ERROR = "database_error"
    PROCESSING_ERROR = "processing_error"
    CANCELLATION = "cancellation"
    UNEXPECTED_ERROR = "unexpected_error"


def classify_failure(error: BaseException) -> FailureCategory:
    name = type(error).__name__.lower()
    if "storage" in name or "file" in name or "oserror" in name:
        return FailureCategory.STORAGE_ERROR
    if "database" in name or "integrity" in name or "operational" in name:
        return FailureCategory.DATABASE_ERROR
    if "csv" in name or "validation" in name:
        return FailureCategory.VALIDATION_ERROR
    return FailureCategory.PROCESSING_ERROR
