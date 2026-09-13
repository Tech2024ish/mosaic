import csv
import io
import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.database.session import SessionLocal, engine
from app.main import app
from app.models.base import Base
from app.models.inventory_snapshot import InventorySnapshot
from app.models.product import Product
from app.models.sales_history import SalesHistory
from app.models.user import User
from app.models.warehouse import Warehouse
from app.services.import_service import create_import_job

Base.metadata.create_all(engine)


def account(client: TestClient) -> tuple[dict[str, str], uuid.UUID]:
    suffix = uuid.uuid4().hex
    payload = {
        "email": f"reports-{suffix}@example.com",
        "name": "Report Owner",
        "password": "Secure password 123!",
    }
    registered = client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    assert login.status_code == 200
    user_id = uuid.UUID(registered.json()["id"])
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        return {"Authorization": f"Bearer {login.json()['access_token']}"}, user.organization_id


def seed_reports(organization_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.organization_id == organization_id))
        assert user is not None
        product = Product(
            organization_id=organization_id,
            product_code="REPORT-P1",
            name="Product, One",
        )
        warehouse = Warehouse(
            organization_id=organization_id,
            warehouse_code="REPORT-W1",
            name="Main Warehouse",
        )
        db.add_all([product, warehouse])
        db.flush()
        job = create_import_job(
            db,
            organization_id,
            user.id,
            "sales_history",
            "reports.csv",
            f"{uuid.uuid4()}.csv",
            uuid.uuid4().hex * 2,
            100,
        )
        db.add_all(
            [
                SalesHistory(
                    organization_id=organization_id,
                    import_job_id=job.id,
                    source_row_number=2,
                    product_code="REPORT-P1",
                    sale_date=date(2026, 1, 5),
                    quantity=Decimal("2"),
                    unit_price=Decimal("10"),
                    warehouse_code="REPORT-W1",
                    row_fingerprint=uuid.uuid4().hex,
                ),
                SalesHistory(
                    organization_id=organization_id,
                    import_job_id=job.id,
                    source_row_number=3,
                    product_code="REPORT-P1",
                    sale_date=date(2026, 2, 5),
                    quantity=Decimal("3"),
                    unit_price=Decimal("10"),
                    warehouse_code="REPORT-W1",
                    row_fingerprint=uuid.uuid4().hex,
                ),
                InventorySnapshot(
                    organization_id=organization_id,
                    product_id=product.id,
                    warehouse_id=warehouse.id,
                    snapshot_date=date(2026, 2, 1),
                    quantity_on_hand=Decimal("75"),
                    unit_cost=Decimal("4.50"),
                ),
            ]
        )
        db.commit()


def test_reports_compose_analytics_and_support_csv_export() -> None:
    client = TestClient(app)
    headers, organization_id = account(client)
    seed_reports(organization_id)

    sales = client.get(
        "/api/v1/reports/sales?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    assert sales.status_code == 200
    body = sales.json()
    assert body["report_type"] == "sales"
    assert body["summary"]["sales_count"] == 1
    assert Decimal(str(body["summary"]["total_revenue"])) == Decimal("20")
    assert body["top_products"][0]["product_code"] == "REPORT-P1"
    assert body["warehouse_performance"][0]["warehouse_code"] == "REPORT-W1"

    products = client.get("/api/v1/reports/products?limit=1", headers=headers)
    assert products.status_code == 200
    assert products.json()["items"][0]["product_name"] == "Product, One"

    inventory = client.get("/api/v1/reports/inventory", headers=headers)
    assert inventory.status_code == 200
    assert inventory.json()["summary"]["inventory_record_count"] == 1
    assert Decimal(str(inventory.json()["items"][0]["quantity_on_hand"])) == Decimal("75")

    warehouses = client.get("/api/v1/reports/warehouses", headers=headers)
    assert warehouses.status_code == 200
    assert warehouses.json()["items"][0]["warehouse_name"] == "Main Warehouse"

    export = client.get("/api/v1/reports/inventory/export?date_from=2026-02-01", headers=headers)
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert "mosaic-inventory-report-2026-02-01-time.csv" in export.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(export.text)))
    assert rows[0] == [
        "product_code",
        "product_name",
        "warehouse_code",
        "warehouse_name",
        "snapshot_date",
        "quantity_on_hand",
        "unit_cost",
    ]
    assert rows[1][1] == "Product, One"


def test_reports_are_tenant_scoped_and_validate_requests() -> None:
    client = TestClient(app)
    first_headers, first_org = account(client)
    second_headers, second_org = account(client)
    seed_reports(first_org)

    second_sales = client.get("/api/v1/reports/sales", headers=second_headers)
    assert second_sales.status_code == 200
    assert second_sales.json()["summary"]["sales_count"] == 0
    assert second_sales.json()["top_products"] == []
    second_export = client.get("/api/v1/reports/sales/export", headers=second_headers)
    assert second_export.status_code == 200
    assert "REPORT-P1" not in second_export.text

    assert client.get("/api/v1/reports/sales").status_code == 401
    assert (
        client.get(
            "/api/v1/reports/sales?date_from=2026-03-01&date_to=2026-01-01",
            headers=first_headers,
        ).status_code
        == 422
    )
    assert client.get("/api/v1/reports/sales?period=year", headers=first_headers).status_code == 422
    assert (
        client.get("/api/v1/reports/sales/export?format=json", headers=first_headers).status_code
        == 422
    )
