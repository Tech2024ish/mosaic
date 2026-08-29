import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import sessionmaker

from app.domain.ingestion.audit_policy import ImportEventType
from app.domain.ingestion.contracts import ValidationIssue
from app.domain.ingestion.csv_parser import CsvFormatError
from app.domain.ingestion.fingerprint import file_fingerprint, row_fingerprint
from app.domain.ingestion.registry import get_dataset_parser
from app.domain.ingestion.retry_policy import can_cancel, can_retry
from app.domain.ingestion.sales import normalize_and_validate
from app.infrastructure.storage.local import LocalFileStorage
from app.models.import_error import ImportError
from app.models.import_event import ImportEvent
from app.models.import_job import ImportJob, ImportStatus
from app.models.sales_history import SalesHistory
from app.models.staging_sales_record import StagingSalesRecord

logger = logging.getLogger(__name__)


class DuplicateImportError(ValueError):
    def __init__(self, existing_job_id: str) -> None:
        super().__init__("This file has already been imported for this organization")
        self.existing_job_id = existing_job_id


class ImportNotRetryableError(ValueError):
    pass


class ImportNotCancellableError(ValueError):
    pass


def create_import_job(
    db: Session,
    organization_id: uuid.UUID,
    created_by: uuid.UUID,
    dataset_type: str,
    original_filename: str,
    storage_key: str,
    content_sha256: str,
    file_size_bytes: int,
) -> ImportJob:
    fingerprint = file_fingerprint(content_sha256, dataset_type, str(organization_id))
    existing = db.scalar(
        select(ImportJob).where(
            ImportJob.organization_id == organization_id,
            ImportJob.dataset_type == dataset_type,
            ImportJob.content_sha256 == content_sha256,
        )
    )
    if existing:
        raise DuplicateImportError(str(existing.id))
    job = ImportJob(
        organization_id=organization_id,
        created_by=created_by,
        dataset_type=dataset_type,
        original_filename=Path(original_filename).name[:255],
        storage_key=storage_key,
        content_sha256=content_sha256,
        file_size_bytes=file_size_bytes,
        status=ImportStatus.PENDING.value,
        processing_metadata={"import_fingerprint": fingerprint},
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateImportError("unknown") from exc
    db.refresh(job)
    record_import_event(db, job, ImportEventType.CREATED, created_by)
    logger.info(
        "Import accepted",
        extra={
            "import_id": str(job.id),
            "organization_id": str(organization_id),
            "user_id": str(created_by),
            "dataset_type": dataset_type,
            "status": job.status,
        },
    )
    return job


def record_import_event(
    db: Session,
    job: ImportJob,
    event_type: ImportEventType,
    actor_id: uuid.UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> ImportEvent:
    event = ImportEvent(
        import_job_id=job.id,
        organization_id=job.organization_id,
        event_type=event_type.value,
        actor_id=actor_id,
        event_metadata=metadata,
        created_at=datetime.now(UTC),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def process_import_job(
    job_id: uuid.UUID, storage: LocalFileStorage, session_factory: sessionmaker[Session]
) -> None:
    db = session_factory()
    job = None
    started = datetime.now(UTC)
    try:
        job = db.scalar(select(ImportJob).where(ImportJob.id == job_id))
        if job is None or job.status != ImportStatus.PENDING.value:
            return
        started_result = cast(
            CursorResult[Any],
            db.execute(
                update(ImportJob)
                .where(ImportJob.id == job.id, ImportJob.status == ImportStatus.PENDING.value)
                .values(status=ImportStatus.PROCESSING.value, started_at=started)
            ),
        )
        if started_result.rowcount != 1:
            db.rollback()
            return
        db.commit()
        db.refresh(job)
        record_import_event(db, job, ImportEventType.PROCESSING_STARTED)
        parser, required_columns, aliases = get_dataset_parser(job.dataset_type)
        valid_rows = []
        errors: list[tuple[ValidationIssue, dict[str, str]]] = []
        total = 0
        with storage.open(job.storage_key) as stream:
            try:
                for parsed in parser(stream, required_columns, aliases):
                    if db.scalar(
                        select(ImportJob.id).where(
                            ImportJob.id == job.id,
                            ImportJob.status == ImportStatus.CANCELLED.value,
                        )
                    ):
                        logger.info(
                            "Import cancelled",
                            extra={
                                "import_id": str(job.id),
                                "organization_id": str(job.organization_id),
                            },
                        )
                        return
                    total += 1
                    normalized, row_issues = normalize_and_validate(parsed)
                    if normalized is not None:
                        valid_rows.append((normalized, parsed.values))
                        staging = StagingSalesRecord(
                            import_job_id=job.id,
                            organization_id=job.organization_id,
                            row_number=parsed.row_number,
                            raw_payload=parsed.values,
                            product_code=normalized.product_code,
                            sale_date=normalized.sale_date,
                            quantity=normalized.quantity,
                            unit_price=normalized.unit_price,
                            warehouse_code=normalized.warehouse_code,
                            is_valid=True,
                        )
                    else:
                        staging = StagingSalesRecord(
                            import_job_id=job.id,
                            organization_id=job.organization_id,
                            row_number=parsed.row_number,
                            raw_payload=parsed.values,
                            is_valid=False,
                        )
                    db.add(staging)
                    errors.extend((issue, parsed.values) for issue in row_issues)
                fingerprints = {row_fingerprint(row) for row, _ in valid_rows}
                existing = set(
                    db.scalars(
                        select(SalesHistory.row_fingerprint).where(
                            SalesHistory.row_fingerprint.in_(fingerprints)
                        )
                    )
                )
                seen: set[str] = set()
                for normalized, raw in valid_rows:
                    fingerprint = row_fingerprint(normalized)
                    if fingerprint in existing or fingerprint in seen:
                        errors.append(
                            (
                                ValidationIssue(
                                    normalized.row_number,
                                    "duplicate_record",
                                    "Duplicate sales record",
                                    None,
                                    None,
                                ),
                                raw,
                            )
                        )
                        continue
                    seen.add(fingerprint)
                    db.add(
                        SalesHistory(
                            organization_id=job.organization_id,
                            import_job_id=job.id,
                            source_row_number=normalized.row_number,
                            product_code=normalized.product_code,
                            sale_date=normalized.sale_date,
                            quantity=normalized.quantity,
                            unit_price=normalized.unit_price,
                            warehouse_code=normalized.warehouse_code,
                            row_fingerprint=fingerprint,
                        )
                    )
            except CsvFormatError:
                raise
        for issue, _raw in errors:
            if issue is not None:
                db.add(
                    ImportError(
                        import_job_id=job.id,
                        row_number=issue.row_number,
                        field_name=issue.field_name,
                        error_code=issue.error_code,
                        message=issue.message,
                        raw_value=issue.raw_value,
                    )
                )
        job.total_rows = total
        job.failed_rows = len([issue for issue, _ in errors if issue is not None])
        job.successful_rows = total - job.failed_rows
        job.error_summary = {
            "error_count": job.failed_rows,
            "codes": sorted({issue.error_code for issue, _ in errors if issue is not None}),
        }
        completed = cast(
            CursorResult[Any],
            db.execute(
                update(ImportJob)
                .where(ImportJob.id == job.id, ImportJob.status == ImportStatus.PROCESSING.value)
                .values(
                    status=ImportStatus.COMPLETED.value,
                    completed_at=datetime.now(UTC),
                    total_rows=total,
                    successful_rows=job.successful_rows,
                    failed_rows=job.failed_rows,
                    error_summary=job.error_summary,
                )
            ),
        )
        if completed.rowcount != 1:
            db.rollback()
            return
        job.status = ImportStatus.COMPLETED.value
        completed_at = datetime.now(UTC)
        job.completed_at = completed_at
        db.commit()
        record_import_event(
            db,
            job,
            ImportEventType.COMPLETED,
            metadata={"total_rows": total, "failed_rows": job.failed_rows},
        )
        logger.info(
            "Import completed",
            extra={
                "import_id": str(job.id),
                "organization_id": str(job.organization_id),
                "dataset_type": job.dataset_type,
                "status": job.status,
                "total_rows": total,
                "successful_rows": job.successful_rows,
                "failed_rows": job.failed_rows,
                "duration_seconds": (completed_at - started).total_seconds(),
            },
        )
    except Exception as exc:
        db.rollback()
        if job is not None:
            job = db.scalar(select(ImportJob).where(ImportJob.id == job_id))
            if job and job.status != ImportStatus.CANCELLED.value:
                job.status = ImportStatus.FAILED.value
                job.completed_at = datetime.now(UTC)
                job.error_summary = {
                    "error_count": 1,
                    "codes": ["processing_failure"],
                    "message": "Import processing failed",
                }
                db.commit()
                record_import_event(
                    db, job, ImportEventType.FAILED, metadata={"failure_reason": type(exc).__name__}
                )
        logger.exception(
            "Import failed", extra={"import_id": str(job_id), "failure_reason": type(exc).__name__}
        )
    finally:
        db.close()


def list_imports(
    db: Session, organization_id: uuid.UUID, offset: int, limit: int
) -> list[ImportJob]:
    return list(
        db.scalars(
            select(ImportJob)
            .where(ImportJob.organization_id == organization_id)
            .order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )


def get_import_for_organization(
    db: Session, import_id: uuid.UUID, organization_id: uuid.UUID
) -> ImportJob | None:
    return db.scalar(
        select(ImportJob).where(
            ImportJob.id == import_id, ImportJob.organization_id == organization_id
        )
    )


def list_import_errors(
    db: Session, import_id: uuid.UUID, offset: int, limit: int
) -> list[ImportError]:
    return list(
        db.scalars(
            select(ImportError)
            .where(ImportError.import_job_id == import_id)
            .order_by(ImportError.row_number, ImportError.id)
            .offset(offset)
            .limit(limit)
        )
    )


def retry_import_job(db: Session, job: ImportJob, actor_id: uuid.UUID) -> ImportJob:
    if not can_retry(job.status):
        raise ImportNotRetryableError("Only failed imports can be retried")
    transitioned = cast(
        CursorResult[Any],
        db.execute(
            update(ImportJob)
            .where(ImportJob.id == job.id, ImportJob.status == ImportStatus.FAILED.value)
            .values(
                status=ImportStatus.PENDING.value,
                started_at=None,
                completed_at=None,
                total_rows=0,
                successful_rows=0,
                failed_rows=0,
                error_summary=None,
            )
        ),
    )
    if transitioned.rowcount != 1:
        db.rollback()
        raise ImportNotRetryableError("Import state changed; retry it again if it is still failed")
    db.execute(delete(ImportError).where(ImportError.import_job_id == job.id))
    db.execute(delete(StagingSalesRecord).where(StagingSalesRecord.import_job_id == job.id))
    db.commit()
    db.refresh(job)
    record_import_event(db, job, ImportEventType.RETRY_REQUESTED, actor_id)
    logger.info(
        "Import retry requested",
        extra={
            "import_id": str(job.id),
            "organization_id": str(job.organization_id),
            "user_id": str(actor_id),
            "status": job.status,
        },
    )
    return job


def cancel_import_job(db: Session, job: ImportJob, actor_id: uuid.UUID) -> ImportJob:
    if not can_cancel(job.status):
        raise ImportNotCancellableError("Only pending or processing imports can be cancelled")
    transitioned = cast(
        CursorResult[Any],
        db.execute(
            update(ImportJob)
            .where(
                ImportJob.id == job.id,
                ImportJob.organization_id == job.organization_id,
                ImportJob.status.in_((ImportStatus.PENDING.value, ImportStatus.PROCESSING.value)),
            )
            .values(status=ImportStatus.CANCELLED.value, completed_at=datetime.now(UTC))
        ),
    )
    if transitioned.rowcount != 1:
        db.rollback()
        raise ImportNotCancellableError("Import state changed; it can no longer be cancelled")
    db.commit()
    db.refresh(job)
    record_import_event(db, job, ImportEventType.CANCELLED, actor_id)
    logger.info(
        "Import cancelled",
        extra={
            "import_id": str(job.id),
            "organization_id": str(job.organization_id),
            "user_id": str(actor_id),
            "status": job.status,
        },
    )
    return job


def list_import_events(
    db: Session, import_id: uuid.UUID, offset: int, limit: int
) -> list[ImportEvent]:
    return list(
        db.scalars(
            select(ImportEvent)
            .where(ImportEvent.import_job_id == import_id)
            .order_by(ImportEvent.created_at, ImportEvent.id)
            .offset(offset)
            .limit(limit)
        )
    )


def import_statistics(db: Session, organization_id: uuid.UUID) -> dict[str, int]:
    row = db.execute(
        select(
            func.count(ImportJob.id),
            func.count(ImportJob.id).filter(ImportJob.status == ImportStatus.COMPLETED.value),
            func.count(ImportJob.id).filter(ImportJob.status == ImportStatus.FAILED.value),
            func.count(ImportJob.id).filter(
                ImportJob.status.in_((ImportStatus.PENDING.value, ImportStatus.PROCESSING.value))
            ),
            func.count(ImportJob.id).filter(ImportJob.status == ImportStatus.CANCELLED.value),
            func.coalesce(func.sum(ImportJob.total_rows), 0),
            func.coalesce(func.sum(ImportJob.successful_rows), 0),
            func.coalesce(func.sum(ImportJob.failed_rows), 0),
        ).where(ImportJob.organization_id == organization_id)
    ).one()
    retry_count = db.scalar(
        select(func.count(ImportEvent.id)).where(
            ImportEvent.organization_id == organization_id,
            ImportEvent.event_type == ImportEventType.RETRY_REQUESTED.value,
        )
    )
    return {
        "total_imports": int(row[0]),
        "successful_imports": int(row[1]),
        "failed_imports": int(row[2]),
        "processing_imports": int(row[3]),
        "cancelled_imports": int(row[4]),
        "retry_count": int(retry_count or 0),
        "total_rows": int(row[5]),
        "successful_rows": int(row[6]),
        "failed_rows": int(row[7]),
    }
