import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.infrastructure.database.session import SessionLocal
from app.main import app
from app.models.import_error import ImportError
from app.models.import_job import ImportJob, ImportStatus
from app.models.user import User
from app.services.import_service import create_import_job


def register_and_login(client: TestClient) -> tuple[dict[str, str], str]:
    payload = {
        "email": f"ops-{uuid.uuid4().hex}@example.com",
        "name": "Operations User",
        "password": "Secure password 123!",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    token = client.post("/api/v1/auth/login", json=payload).json()["access_token"]
    return payload, token


def make_job(email: str, status: str) -> uuid.UUID:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        job = create_import_job(
            db,
            user.organization_id,
            user.id,
            "sales_history",
            "sales.csv",
            f"{uuid.uuid4()}.csv",
            uuid.uuid4().hex * 2,
            100,
        )
        storage_path = Path(get_settings().storage_root)
        storage_path.mkdir(parents=True, exist_ok=True)
        (storage_path / job.storage_key).write_text(
            "product_code,sale_date,quantity,unit_price,warehouse_code\nP-1,2026-01-01,1,10,JHB\n",
            encoding="utf-8",
        )
        job.status = status
        job.total_rows = 10
        job.successful_rows = 8
        job.failed_rows = 2
        db.add(
            ImportError(
                import_job_id=job.id,
                row_number=3,
                error_code="invalid_date",
                message="Invalid date",
            )
        )
        db.commit()
        return job.id


def test_history_detail_errors_and_stats_are_tenant_scoped() -> None:
    client = TestClient(app)
    first, token = register_and_login(client)
    second, second_token = register_and_login(client)
    own_id = make_job(first["email"], ImportStatus.FAILED.value)
    other_id = make_job(second["email"], ImportStatus.COMPLETED.value)
    headers = {"Authorization": f"Bearer {token}"}

    history = client.get("/api/v1/imports?limit=1", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == str(own_id)
    assert client.get(f"/api/v1/imports/{own_id}", headers=headers).status_code == 200
    assert (
        client.get(f"/api/v1/imports/{own_id}/errors", headers=headers).json()[0]["row_number"] == 3
    )
    assert client.get(f"/api/v1/imports/{other_id}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/imports/{other_id}/errors", headers=headers).status_code == 404
    assert client.get("/api/v1/imports/stats", headers=headers).json()["total_imports"] == 1
    assert client.get("/api/v1/imports", headers={"Authorization": f"Bearer {second_token}"}).json()
    assert client.get("/api/v1/imports").status_code == 401


def test_failed_import_can_retry_but_completed_import_cannot() -> None:
    client = TestClient(app)
    first, token = register_and_login(client)
    failed_id = make_job(first["email"], ImportStatus.FAILED.value)
    completed_id = make_job(first["email"], ImportStatus.COMPLETED.value)
    headers = {"Authorization": f"Bearer {token}"}

    retry = client.post(f"/api/v1/imports/{failed_id}/retry", headers=headers)
    assert retry.status_code == 200
    assert retry.json()["status"] == "pending"
    assert client.post(f"/api/v1/imports/{completed_id}/retry", headers=headers).status_code == 409
    with SessionLocal() as db:
        job = db.get(ImportJob, failed_id)
        assert job is not None and job.status == ImportStatus.COMPLETED.value


def test_retry_cannot_cross_tenant_boundary() -> None:
    client = TestClient(app)
    first, first_token = register_and_login(client)
    second, second_token = register_and_login(client)
    failed_id = make_job(first["email"], ImportStatus.FAILED.value)
    response = client.post(
        f"/api/v1/imports/{failed_id}/retry",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert response.status_code == 404
    assert (
        client.post(
            f"/api/v1/imports/{failed_id}/retry",
            headers={"Authorization": f"Bearer {first_token}"},
        ).status_code
        == 200
    )
