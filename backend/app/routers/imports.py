import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.infrastructure.database.session import SessionLocal, get_db
from app.infrastructure.storage.local import FileTooLargeError, LocalFileStorage
from app.models.import_error import ImportError
from app.models.import_job import ImportJob
from app.models.user import User
from app.schemas.imports import DatasetType, ImportErrorResponse, ImportJobResponse
from app.services.import_service import DuplicateImportError, create_import_job, process_import_job

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


@router.get("/{import_id}", response_model=ImportJobResponse)
def get_import(
    import_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportJob:
    return get_owned_import(db, import_id, current_user.organization_id)


@router.get("/{import_id}/errors", response_model=list[ImportErrorResponse])
def get_import_errors(
    import_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ImportError]:
    get_owned_import(db, import_id, current_user.organization_id)
    return list(
        db.scalars(
            select(ImportError)
            .where(ImportError.import_job_id == import_id)
            .order_by(ImportError.row_number)
        )
    )
