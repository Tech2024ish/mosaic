import shutil
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.infrastructure.storage.local import LocalFileStorage
from app.models.base import Base
from app.models.import_error import ImportError
from app.models.import_job import ImportStatus
from app.models.organization import Organization
from app.models.sales_history import SalesHistory
from app.models.staging_sales_record import StagingSalesRecord
from app.models.user import User
from app.services.import_service import DuplicateImportError, create_import_job, process_import_job


def test_import_persists_valid_rows_and_isolates_tenant() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    org_a = Organization(name="A", slug="a")
    org_b = Organization(name="B", slug="b")
    db.add_all([org_a, org_b])
    db.flush()
    user_a = User(
        organization_id=org_a.id, email="a@example.com", password_hash=hash_password("password")
    )
    user_b = User(
        organization_id=org_b.id, email="b@example.com", password_hash=hash_password("password")
    )
    db.add_all([user_a, user_b])
    db.commit()
    storage_root = Path(".test-storage")
    storage = LocalFileStorage(str(storage_root), 1_000_000)
    key = "sample.upload"
    try:
        (storage_root / key).write_text(
            "SKU,Date,Qty,Price,Warehouse\nP-1,2026-01-02,2,10,JHB\nP-2,bad,1,5,JHB\nP-1,2026-01-02,2,10,JHB\n",
            encoding="utf-8",
        )
        job = create_import_job(
            db, org_a.id, user_a.id, "sales_history", "../sales.csv", key, "a" * 64, 120
        )
        process_import_job(job.id, storage, session_factory)
        db.expire_all()
        stored = db.get(type(job), job.id)
        assert stored is not None
        assert stored.status == ImportStatus.COMPLETED.value
        assert (stored.total_rows, stored.successful_rows, stored.failed_rows) == (3, 1, 2)
        assert (
            db.scalar(select(SalesHistory).where(SalesHistory.organization_id == org_a.id))
            is not None
        )
        assert (
            db.scalar(select(SalesHistory).where(SalesHistory.organization_id == org_b.id)) is None
        )
        assert (
            db.scalar(
                select(StagingSalesRecord).where(StagingSalesRecord.organization_id == org_a.id)
            )
            is not None
        )
        assert db.scalar(select(ImportError).where(ImportError.import_job_id == job.id)) is not None
        assert stored.original_filename == "sales.csv"
        try:
            create_import_job(
                db,
                org_a.id,
                user_a.id,
                "sales_history",
                "another-name.csv",
                "other.upload",
                "a" * 64,
                120,
            )
        except DuplicateImportError:
            pass
        else:
            raise AssertionError("same tenant/dataset/content must be idempotent")
    finally:
        db.close()
        shutil.rmtree(storage_root, ignore_errors=True)
