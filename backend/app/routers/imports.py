import csv
import io
import uuid
from collections.abc import Generator

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.infrastructure.database.session import SessionLocal, get_db
from app.infrastructure.storage.local import FileTooLargeError, LocalFileStorage
from app.models.import_error import ImportError
from app.models.import_event import ImportEvent
from app.models.import_job import ImportJob
from app.models.user import User
from app.schemas.imports import (
    CancelResponse,
    DatasetType,
    ImportErrorResponse,
    ImportEventResponse,
    ImportJobResponse,
    ImportStatsResponse,
    RetryResponse,
)
from app.schemas.imports import (
    ImportStatus as ImportStatusSchema,
)
from app.services.import_service import (
    DuplicateImportError,
    ImportNotCancellableError,
    ImportNotRetryableError,
    cancel_import_job,
    create_import_job,
    get_import_for_organization,
    import_statistics,
    list_import_errors,
    list_import_events,
    list_imports,
    process_import_job,
    retry_import_job,
)

router = APIRouter(prefix="/imports", tags=["imports"])


def storage() -> LocalFileStorage:
    settings = get_settings()
    return LocalFileStorage(settings.storage_root, settings.max_upload_size_bytes)


def get_owned_import(db: Session, import_id: uuid.UUID, organization_id: uuid.UUID) -> ImportJob:
    job = db.scalar(
        select(ImportJob).where(
            ImportJob.id == import_id, ImportJob.organization_id == organization_id
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    return job


@router.post("", response_model=ImportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    dataset_type: DatasetType = DatasetType.SALES_HISTORY,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportJob:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")
    file_storage = storage()
    try:
        storage_key, size, digest = await file_storage.save_upload(file)
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Upload storage is unavailable") from exc
    try:
        job = create_import_job(
            db,
            current_user.organization_id,
            current_user.id,
            dataset_type.value,
            file.filename,
            storage_key,
            digest,
            size,
        )
    except DuplicateImportError as exc:
        file_storage.delete(storage_key)
        raise HTTPException(
            status_code=409, detail={"message": str(exc), "existing_import_id": exc.existing_job_id}
        ) from exc
    background_tasks.add_task(process_import_job, job.id, file_storage, SessionLocal)
    return job


@router.get("/stats", response_model=ImportStatsResponse)
def get_import_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, int]:
    return import_statistics(db, current_user.organization_id)


@router.get("", response_model=list[ImportJobResponse])
def get_import_history(
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ImportJob]:
    if offset < 0 or limit < 1 or limit > 100:
        raise HTTPException(
            status_code=422, detail="offset must be non-negative and limit must be 1-100"
        )
    return list_imports(db, current_user.organization_id, offset, limit)


@router.get("/{import_id}", response_model=ImportJobResponse)
def get_import(
    import_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportJob:
    return get_owned_import(db, import_id, current_user.organization_id)


@router.get("/{import_id}/errors/report")
def download_error_report(
    import_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    job = get_owned_import(db, import_id, current_user.organization_id)

    def report_rows() -> Generator[str, None, None]:
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("row_number", "field_name", "error_message"))
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        with SessionLocal() as report_db:
            report_query = report_db.scalars(
                select(ImportError)
                .where(ImportError.import_job_id == job.id)
                .order_by(ImportError.row_number, ImportError.id)
            )
            for error in report_query.yield_per(1000):
                writer.writerow((error.row_number, error.field_name or "", error.message))
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

    return StreamingResponse(
        report_rows(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="mosaic-import-{job.id}-errors.csv"'
        },
    )


@router.get("/{import_id}/errors", response_model=list[ImportErrorResponse])
def get_import_errors(
    import_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ImportError]:
    get_owned_import(db, import_id, current_user.organization_id)
    if offset < 0 or limit < 1 or limit > 100:
        raise HTTPException(
            status_code=422, detail="offset must be non-negative and limit must be 1-100"
        )
    return list_import_errors(db, import_id, offset, limit)


@router.get("/{import_id}/events", response_model=list[ImportEventResponse])
def get_import_events(
    import_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ImportEvent]:
    get_owned_import(db, import_id, current_user.organization_id)
    if offset < 0 or limit < 1 or limit > 100:
        raise HTTPException(
            status_code=422, detail="offset must be non-negative and limit must be 1-100"
        )
    return list_import_events(db, import_id, offset, limit)


@router.post("/{import_id}/retry", response_model=RetryResponse)
def retry_import(
    import_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RetryResponse:
    job = get_import_for_organization(db, import_id, current_user.organization_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    try:
        retry_import_job(db, job, current_user.id)
    except ImportNotRetryableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    file_storage = storage()
    background_tasks.add_task(process_import_job, job.id, file_storage, SessionLocal)
    return RetryResponse(
        import_id=job.id,
        status=ImportStatusSchema(job.status),
        message="Import queued for retry",
    )


@router.post("/{import_id}/cancel", response_model=CancelResponse)
def cancel_import(
    import_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CancelResponse:
    job = get_import_for_organization(db, import_id, current_user.organization_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    try:
        cancel_import_job(db, job, current_user.id)
    except ImportNotCancellableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CancelResponse(
        import_id=job.id, status=ImportStatusSchema(job.status), message="Import cancelled"
    )
