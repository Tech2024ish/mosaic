import uuid
from datetime import date
from decimal import Decimal

from conftest import verify_test_user
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


def account(client: TestClient, prefix: str) -> tuple[dict[str, str], uuid.UUID]:
    email = f"insights-{prefix}-{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "name": "Insights Owner", "password": "Secure password 123!"}
    registered = client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 201
    verify_test_user(email)
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": payload["password"]}
    )
    assert login.status_code == 200
    user_id = uuid.UUID(registered.json()["id"])
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        return {"Authorization": f"Bearer {login.json()['access_token']}"}, user.organization_id


def seed(organization_id: uuid.UUID, prefix: str, revenue: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.organization_id == organization_id))
        assert user is not None
        product = Product(
            organization_id=organization_id, product_code=f"{prefix}-P", name="Insight Product"
        )
        warehouse = Warehouse(
            organization_id=organization_id, warehouse_code=f"{prefix}-W", name="Insight Warehouse"
        )
        db.add_all([product, warehouse])
        db.flush()
        job = create_import_job(
            db,
            organization_id,
            user.id,
            "sales_history",
            f"{prefix}.csv",
            f"{uuid.uuid4()}.csv",
            uuid.uuid4().hex * 2,
            10,
        )
        db.add_all(
            [
                SalesHistory(
                    organization_id=organization_id,
                    import_job_id=job.id,
                    source_row_number=1,
                    product_code=product.product_code,
                    sale_date=date(2026, 2, 10),
                    quantity=Decimal("2"),
                    unit_price=Decimal(revenue),
                    warehouse_code=warehouse.warehouse_code,
                    row_fingerprint=uuid.uuid4().hex * 2,
                ),
                InventorySnapshot(
                    organization_id=organization_id,
                    product_id=product.id,
                    warehouse_id=warehouse.id,
                    snapshot_date=date(2026, 2, 10),
                    quantity_on_hand=Decimal("0"),
                ),
            ]
        )
        db.commit()


def test_insights_overview_is_deterministic_and_tenant_scoped() -> None:
    client = TestClient(app)
    first_headers, first_org = account(client, "first")
    second_headers, second_org = account(client, "second")
    seed(first_org, "FIRST", "10")
    seed(second_org, "SECOND", "900")

    response = client.get(
        "/api/v1/insights/overview?date_from=2026-02-01&date_to=2026-02-28",
        headers=first_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_revenue"] == "20.0000"
    assert body["top_products"][0]["product_code"] == "FIRST-P"
    assert body["inventory"]["out_of_stock_products"] == 1
    assert body["insights"][0]["code"] == "revenue_concentration"
    assert client.get("/api/v1/insights/overview").status_code == 401
    assert second_headers["Authorization"] != first_headers["Authorization"]


def test_period_comparison_handles_previous_zero_and_tenant_scope() -> None:
    client = TestClient(app)
    headers, organization_id = account(client, "comparison")
    seed(organization_id, "COMPARE", "25")

    response = client.get(
        "/api/v1/insights/comparison?date_from=2026-02-10&date_to=2026-02-10",
        headers=headers,
    )
    assert response.status_code == 200
    metrics = {item["name"]: item for item in response.json()["metrics"]}
    assert metrics["revenue"]["current_value"] == "50.0000"
    assert metrics["revenue"]["previous_value"] == "0.0000"
    assert metrics["revenue"]["change_percent"] is None
    assert metrics["revenue"]["category"] == "positive"

    invalid = client.get(
        "/api/v1/insights/comparison?date_from=2026-02-11&date_to=2026-02-10",
        headers=headers,
    )
    assert invalid.status_code == 422
