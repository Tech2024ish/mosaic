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
from app.models.supplier import Supplier
from app.models.user import User
from app.models.warehouse import Warehouse
from app.services.import_service import create_import_job

Base.metadata.create_all(engine)


def account(client: TestClient) -> tuple[dict[str, str], uuid.UUID]:
    suffix = uuid.uuid4().hex
    payload = {
        "email": f"analytics-{suffix}@example.com",
        "name": "Analytics Owner",
        "password": "Secure password 123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    login = client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    assert login.status_code == 200
    user_id = uuid.UUID(response.json()["id"])
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        return {"Authorization": f"Bearer {login.json()['access_token']}"}, user.organization_id


def seed_tenant(
    organization_id: uuid.UUID,
    product_prefix: str,
    warehouse_prefix: str,
    sales: list[tuple[str, date, str, str, str]],
) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.organization_id == organization_id))
        assert user is not None
        product_one = Product(
            organization_id=organization_id,
            product_code=f"{product_prefix}-1",
            name="Alpha Product",
        )
        product_two = Product(
            organization_id=organization_id,
            product_code=f"{product_prefix}-2",
            name="Beta Product",
        )
        warehouse_one = Warehouse(
            organization_id=organization_id,
            warehouse_code=f"{warehouse_prefix}-1",
            name="Central Warehouse",
        )
        warehouse_two = Warehouse(
            organization_id=organization_id,
            warehouse_code=f"{warehouse_prefix}-2",
            name="East Warehouse",
        )
        supplier = Supplier(
            organization_id=organization_id,
            supplier_code=f"{product_prefix}-SUPPLIER",
            name="Primary Supplier",
        )
        db.add_all([product_one, product_two, warehouse_one, warehouse_two, supplier])
        db.flush()
        job = create_import_job(
            db,
            organization_id,
            user.id,
            "sales_history",
            "analytics.csv",
            f"{uuid.uuid4()}.csv",
            uuid.uuid4().hex * 2,
            100,
        )
        db.add_all(
            [
                SalesHistory(
                    organization_id=organization_id,
                    import_job_id=job.id,
                    source_row_number=index + 2,
                    product_code=product_code,
                    sale_date=sale_date,
                    quantity=Decimal(quantity),
                    unit_price=Decimal(unit_price),
                    warehouse_code=warehouse_code,
                    row_fingerprint=uuid.uuid4().hex,
                )
                for index, (
                    product_code,
                    sale_date,
                    quantity,
                    unit_price,
                    warehouse_code,
                ) in enumerate(sales)
            ]
        )
        db.add_all(
            [
                InventorySnapshot(
                    organization_id=organization_id,
                    product_id=product_one.id,
                    warehouse_id=warehouse_one.id,
                    snapshot_date=date(2026, 1, 1),
                    quantity_on_hand=Decimal("100"),
                ),
                InventorySnapshot(
                    organization_id=organization_id,
                    product_id=product_one.id,
                    warehouse_id=warehouse_one.id,
                    snapshot_date=date(2026, 2, 1),
                    quantity_on_hand=Decimal("80"),
                ),
                InventorySnapshot(
                    organization_id=organization_id,
                    product_id=product_two.id,
                    warehouse_id=warehouse_two.id,
                    snapshot_date=date(2026, 2, 1),
                    quantity_on_hand=Decimal("20"),
                ),
            ]
        )
        db.commit()


def test_analytics_summary_and_filters_are_database_aggregates() -> None:
    client = TestClient(app)
    headers, organization_id = account(client)
    seed_tenant(
        organization_id,
        "ANALYTICS-A",
        "WH-A",
        [
            ("ANALYTICS-A-1", date(2026, 1, 5), "2", "10", "WH-A-1"),
            ("ANALYTICS-A-1", date(2026, 1, 20), "3", "10", "WH-A-1"),
            ("ANALYTICS-A-2", date(2026, 2, 1), "1", "50", "WH-A-2"),
        ],
    )

    summary = client.get("/api/v1/analytics/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["sales_count"] == 3
    assert Decimal(str(summary.json()["total_quantity"])) == Decimal("6")
    assert Decimal(str(summary.json()["total_revenue"])) == Decimal("100")
    assert Decimal(str(summary.json()["inventory_quantity"])) == Decimal("100")
    assert summary.json()["inventory_record_count"] == 2

    january = client.get(
        "/api/v1/analytics/sales?date_from=2026-01-01&date_to=2026-01-31",
        headers=headers,
    )
    assert january.status_code == 200
    assert january.json()["sales_count"] == 2
    assert Decimal(str(january.json()["total_revenue"])) == Decimal("50")

    trend = client.get("/api/v1/analytics/sales/trend?period=month", headers=headers)
    assert trend.status_code == 200
    assert [(item["period"], item["sales_count"]) for item in trend.json()["data"]] == [
        ("2026-01", 2),
        ("2026-02", 1),
    ]

    top = client.get("/api/v1/analytics/products/top?limit=1", headers=headers)
    assert top.status_code == 200
    assert top.json()["items"][0]["product_code"] == "ANALYTICS-A-1"
    assert top.json()["items"][0]["product_name"] == "Alpha Product"

    warehouses = client.get("/api/v1/analytics/warehouses/performance?limit=1", headers=headers)
    assert warehouses.status_code == 200
    assert warehouses.json()["items"][0]["warehouse_code"] == "WH-A-1"

    inventory = client.get("/api/v1/analytics/inventory?date_from=2026-02-01", headers=headers)
    assert inventory.status_code == 200
    assert inventory.json()["inventory_record_count"] == 2
    assert Decimal(str(inventory.json()["total_quantity"])) == Decimal("100")


def test_analytics_is_tenant_scoped_and_validates_queries() -> None:
    client = TestClient(app)
    first_headers, first_org = account(client)
    second_headers, second_org = account(client)
    seed_tenant(
        first_org,
        "TENANT-A",
        "TENANT-W-A",
        [("TENANT-A-1", date(2026, 1, 1), "4", "25", "TENANT-W-A-1")],
    )
    seed_tenant(
        second_org,
        "TENANT-B",
        "TENANT-W-B",
        [("TENANT-B-1", date(2026, 1, 1), "9", "100", "TENANT-W-B-1")],
    )

    first_summary = client.get("/api/v1/analytics/summary", headers=first_headers)
    second_summary = client.get("/api/v1/analytics/summary", headers=second_headers)
    assert first_summary.json()["sales_count"] == 1
    assert second_summary.json()["sales_count"] == 1
    assert Decimal(str(first_summary.json()["total_revenue"])) == Decimal("100")
    assert Decimal(str(second_summary.json()["total_revenue"])) == Decimal("900")
    assert (
        client.get("/api/v1/analytics/products/top", headers=first_headers).json()["items"][0][
            "product_code"
        ]
        == "TENANT-A-1"
    )
    assert (
        client.get("/api/v1/analytics/products/top", headers=second_headers).json()["items"][0][
            "product_code"
        ]
        == "TENANT-B-1"
    )
    first_grouped = client.get("/api/v1/analytics/sales?group_by=product", headers=first_headers)
    second_grouped = client.get("/api/v1/analytics/sales?group_by=product", headers=second_headers)
    assert first_grouped.json()["groups"][0]["key"] == "TENANT-A-1"
    assert second_grouped.json()["groups"][0]["key"] == "TENANT-B-1"
    assert "TENANT-B-1" not in {item["key"] for item in first_grouped.json()["groups"]}

    assert client.get("/api/v1/analytics/summary").status_code == 401
    assert (
        client.get(
            "/api/v1/analytics/sales?date_from=2026-02-01&date_to=2026-01-01",
            headers=first_headers,
        ).status_code
        == 422
    )
    assert (
        client.get("/api/v1/analytics/sales/trend?period=year", headers=first_headers).status_code
        == 422
    )
    assert (
        client.get("/api/v1/analytics/products/top?limit=101", headers=first_headers).status_code
        == 422
    )


def test_sales_query_supports_safe_grouping_and_filters() -> None:
    client = TestClient(app)
    headers, organization_id = account(client)
    seed_tenant(
        organization_id,
        "QUERY-A",
        "QUERY-W-A",
        [
            ("QUERY-A-1", date(2026, 3, 1), "2", "10.1250", "QUERY-W-A-1"),
            ("QUERY-A-1", date(2026, 3, 1), "1", "10.1250", "QUERY-W-A-1"),
            ("QUERY-A-2", date(2026, 3, 2), "4", "5", "QUERY-W-A-2"),
        ],
    )

    by_date = client.get("/api/v1/analytics/sales?group_by=date&period=day", headers=headers)
    assert by_date.status_code == 200
    assert [(item["key"], item["sales_count"]) for item in by_date.json()["groups"]] == [
        ("2026-03-01", 2),
        ("2026-03-02", 1),
    ]
    assert Decimal(str(by_date.json()["groups"][0]["total_revenue"])) == Decimal("30.3750")

    by_product = client.get(
        "/api/v1/analytics/sales?group_by=product&product_code=QUERY-A-1&limit=1",
        headers=headers,
    )
    assert by_product.status_code == 200
    assert by_product.json()["groups"][0]["key"] == "QUERY-A-1"
    assert by_product.json()["groups"][0]["label"] == "Alpha Product"
    assert by_product.json()["groups"][0]["sales_count"] == 2

    by_warehouse = client.get("/api/v1/analytics/sales?group_by=warehouse", headers=headers)
    assert by_warehouse.status_code == 200
    assert by_warehouse.json()["groups"][0]["key"] == "QUERY-W-A-1"

    empty = client.get(
        "/api/v1/analytics/sales?group_by=product&product_code=missing", headers=headers
    )
    assert empty.status_code == 200
    assert empty.json()["groups"] == []
    assert (
        client.get("/api/v1/analytics/sales?group_by=unknown", headers=headers).status_code == 422
    )
