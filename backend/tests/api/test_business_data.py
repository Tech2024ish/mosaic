import uuid
from datetime import date
from decimal import Decimal

from conftest import verify_test_user
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.database.session import SessionLocal
from app.main import app
from app.models.sales_history import SalesHistory
from app.models.user import User
from app.services.import_service import create_import_job


def account(client: TestClient) -> tuple[dict[str, str], str]:
    payload = {
        "email": f"data-{uuid.uuid4().hex}@example.com",
        "name": "Data Explorer",
        "password": "Secure password 123!",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    verify_test_user(payload["email"])
    token = client.post("/api/v1/auth/login", json=payload).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, payload["email"]


def test_products_search_sort_pagination_and_tenant_isolation() -> None:
    client = TestClient(app)
    first, _ = account(client)
    second, _ = account(client)
    for code, name in (("P-1", "Alpha"), ("P-2", "Beta"), ("P-3", "Alpha Plus")):
        assert (
            client.post(
                "/api/v1/products", json={"product_code": code, "name": name}, headers=first
            ).status_code
            == 201
        )
    response = client.get(
        "/api/v1/products?search=alpha&sort=name&order=asc&limit=2", headers=first
    )
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Alpha", "Alpha Plus"]
    assert client.get("/api/v1/products?sort=not_allowed", headers=first).status_code == 422
    assert client.get("/api/v1/products?limit=101", headers=first).status_code == 422
    assert client.get("/api/v1/products", headers=second).json() == []
    assert client.get("/api/v1/products/not-a-uuid", headers=first).status_code == 422


def test_inventory_filters_and_sales_are_tenant_scoped() -> None:
    client = TestClient(app)
    first, email = account(client)
    second, _ = account(client)
    product = client.post(
        "/api/v1/products", json={"product_code": "P-SALES", "name": "Sales item"}, headers=first
    ).json()
    warehouse = client.post(
        "/api/v1/warehouses",
        json={"warehouse_code": "W-SALES", "name": "Sales warehouse"},
        headers=first,
    ).json()
    snapshot = client.post(
        "/api/v1/inventory",
        json={
            "product_id": product["id"],
            "warehouse_id": warehouse["id"],
            "snapshot_date": "2026-05-01",
            "quantity_on_hand": 25,
        },
        headers=first,
    )
    assert snapshot.status_code == 201
    filtered = client.get(
        f"/api/v1/inventory?product_id={product['id']}&snapshot_date_from=2026-05-01",
        headers=first,
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert (
        client.get(
            "/api/v1/inventory?snapshot_date_from=2026-06-01&snapshot_date_to=2026-05-01",
            headers=first,
        ).status_code
        == 422
    )
    assert client.get("/api/v1/inventory", headers=second).json() == []

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
            10,
        )
        db.add(
            SalesHistory(
                organization_id=user.organization_id,
                import_job_id=job.id,
                source_row_number=2,
                product_code="P-SALES",
                sale_date=date(2026, 5, 1),
                quantity=Decimal("3"),
                unit_price=Decimal("10"),
                warehouse_code="W-SALES",
                row_fingerprint=uuid.uuid4().hex,
            )
        )
        db.commit()
        sale_id = db.scalar(select(SalesHistory.id).where(SalesHistory.import_job_id == job.id))
    assert sale_id is not None
    sales = client.get(
        "/api/v1/sales?product_code=p-sales&sale_date_from=2026-05-01", headers=first
    )
    assert sales.status_code == 200
    assert len(sales.json()) == 1
    assert client.get("/api/v1/sales", headers=second).json() == []
    assert client.get(f"/api/v1/sales/{sale_id}", headers=second).status_code == 404
