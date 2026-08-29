from app.models.import_job import ImportStatus


def can_retry(status: str) -> bool:
    """Only terminal failed jobs can be re-queued."""
    return status == ImportStatus.FAILED.value


def can_cancel(status: str) -> bool:
    """Pending and processing jobs support cooperative cancellation."""
    return status in (ImportStatus.PENDING.value, ImportStatus.PROCESSING.value)
