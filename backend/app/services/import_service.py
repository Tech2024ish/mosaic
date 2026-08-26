import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import sessionmaker

from app.domain.ingestion.contracts import ValidationIssue
from app.domain.ingestion.csv_parser import CsvFormatError
from app.domain.ingestion.fingerprint import file_fingerprint, row_fingerprint
from app.domain.ingestion.registry import get_dataset_parser
from app.domain.ingestion.sales import normalize_and_validate
from app.infrastructure.storage.local import LocalFileStorage
from app.models.import_error import ImportError
from app.models.import_job import ImportJob, ImportStatus
from app.models.sales_history import SalesHistory
from app.models.staging_sales_record import StagingSalesRecord

logger = logging.getLogger(__name__)


class DuplicateImportError(ValueError):
    def __init__(self, existing_job_id: str) -> None:
        super().__init__("This file has already been imported for this organization")
        self.existing_job_id = existing_job_id


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
    return job


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
        job.status = ImportStatus.PROCESSING.value
        job.started_at = started
        db.commit()
        parser, required_columns, aliases = get_dataset_parser(job.dataset_type)
        valid_rows = []
        errors: list[tuple[ValidationIssue, dict[str, str]]] = []
        total = 0
        with storage.open(job.storage_key) as stream:
            try:
                for parsed in parser(stream, required_columns, aliases):
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
        job.status = ImportStatus.COMPLETED.value
        completed_at = datetime.now(UTC)
        job.completed_at = completed_at
        db.commit()
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
            if job:
                job.status = ImportStatus.FAILED.value
                job.completed_at = datetime.now(UTC)
                job.error_summary = {
                    "error_count": 1,
                    "codes": ["processing_failure"],
                    "message": "Import processing failed",
                }
                db.commit()
        logger.exception(
            "Import failed", extra={"import_id": str(job_id), "failure_reason": type(exc).__name__}
        )
    finally:
        db.close()
