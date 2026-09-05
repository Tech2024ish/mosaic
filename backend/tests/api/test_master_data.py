import io
import uuid

from fastapi.testclient import TestClient

from app.main import app


def account(client: TestClient) -> tuple[dict[str, str], dict[str, str]]:
    payload = {
        "email": f"master-{uuid.uuid4().hex}@example.com",
        "name": "Master Data Owner",
        "password": "Secure password 123!",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    token = client.post("/api/v1/auth/login", json=payload).json()["access_token"]
    return payload, {"Authorization": f"Bearer {token}"}


def test_master_data_crud_is_tenant_scoped() -> None:
    client = TestClient(app)
    _, first_headers = account(client)
    _, second_headers = account(client)

    product = client.post(
        "/api/v1/products",
        json={"product_code": " sku-1 ", "name": "Widget"},
        headers=first_headers,
    )
    assert product.status_code == 201
    product_body = product.json()
    assert product_body["product_code"] == "SKU-1"
    assert (
        client.post(
            "/api/v1/products",
            json={"product_code": "SKU-1", "name": "Duplicate"},
            headers=first_headers,
        ).status_code
        == 409
    )
    assert client.get("/api/v1/products", headers=second_headers).json() == []
    assert client.get("/api/v1/products?limit=101", headers=first_headers).status_code == 422
    assert (
        client.get(f"/api/v1/products/{product_body['id']}", headers=second_headers).status_code
        == 404
    )
    updated = client.patch(
        f"/api/v1/products/{product_body['id']}",
        json={"name": "Updated widget", "is_active": False},
        headers=first_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    warehouse = client.post(
        "/api/v1/warehouses",
        json={"warehouse_code": "JHB", "name": "Johannesburg"},
        headers=first_headers,
    )
    supplier = client.post(
        "/api/v1/suppliers",
        json={"supplier_code": "SUP-1", "name": "Reliable Supplier"},
        headers=first_headers,
    )
    assert warehouse.status_code == 201
    assert supplier.status_code == 201
    assert client.get("/api/v1/warehouses", headers=second_headers).json() == []
    assert client.get("/api/v1/suppliers", headers=second_headers).json() == []

    snapshot = client.post(
        "/api/v1/inventory",
        json={
            "product_id": product_body["id"],
            "warehouse_id": warehouse.json()["id"],
            "snapshot_date": "2026-01-01",
            "quantity_on_hand": "12.5",
            "unit_cost": "4.25",
        },
        headers=first_headers,
    )
    assert snapshot.status_code == 201
    assert client.get("/api/v1/inventory", headers=second_headers).json() == []
    assert (
        client.get(f"/api/v1/inventory/{snapshot.json()['id']}", headers=second_headers).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/inventory",
            json={
                "product_id": product_body["id"],
                "warehouse_id": warehouse.json()["id"],
                "snapshot_date": "2026-01-01",
                "quantity_on_hand": 13,
            },
            headers=first_headers,
        ).status_code
        == 409
    )


def test_inventory_rejects_cross_tenant_references() -> None:
    client = TestClient(app)
    _, first_headers = account(client)
    _, second_headers = account(client)
    product = client.post(
        "/api/v1/products", json={"product_code": "P-1", "name": "Product"}, headers=first_headers
    ).json()
    warehouse = client.post(
        "/api/v1/warehouses",
        json={"warehouse_code": "W-1", "name": "Warehouse"},
        headers=first_headers,
    ).json()
    response = client.post(
        "/api/v1/inventory",
        json={
            "product_id": product["id"],
            "warehouse_id": warehouse["id"],
            "snapshot_date": "2026-02-01",
            "quantity_on_hand": 1,
        },
        headers=second_headers,
    )
    assert response.status_code == 409


def test_master_dataset_csv_import_uses_shared_pipeline() -> None:
    client = TestClient(app)
    _, headers = account(client)
    csv_data = b"product_code,product_name,description,category,unit_of_measure,is_active\nP-CSV,CSV Product,,,each,true\nP-CSV,Duplicate,,,,true\n"
    response = client.post(
        "/api/v1/imports",
        files={"file": ("products.csv", io.BytesIO(csv_data), "text/csv")},
        data={"dataset_type": "products"},
        headers=headers,
    )
    assert response.status_code == 202
    job = client.get(f"/api/v1/imports/{response.json()['id']}", headers=headers).json()
    assert job["status"] == "completed"
    assert job["total_rows"] == 2
    assert job["successful_rows"] == 1
    assert job["failed_rows"] == 1
    attempts = client.get(f"/api/v1/imports/{job['id']}/attempts", headers=headers)
    assert attempts.status_code == 200
    assert attempts.json()[0]["attempt_number"] == 1
    assert attempts.json()[0]["status"] == "completed"
    assert client.get("/api/v1/products", headers=headers).json()[0]["product_code"] == "P-CSV"
    errors = client.get(f"/api/v1/imports/{job['id']}/errors", headers=headers)
    assert errors.status_code == 200
    assert errors.json()[0]["error_code"] == "duplicate_record"


def test_inventory_csv_import_resolves_tenant_owned_references() -> None:
    client = TestClient(app)
    _, headers = account(client)
    assert (
        client.post(
            "/api/v1/products",
            json={"product_code": "P-INV", "name": "Inventory Product"},
            headers=headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/warehouses",
            json={"warehouse_code": "W-INV", "name": "Inventory Warehouse"},
            headers=headers,
        ).status_code
        == 201
    )
    csv_data = b"snapshot_date,product_code,warehouse_code,quantity_on_hand,unit_cost\n2026-03-01,P-INV,W-INV,20,3.50\n"
    response = client.post(
        "/api/v1/imports",
        files={"file": ("inventory.csv", io.BytesIO(csv_data), "text/csv")},
        data={"dataset_type": "inventory_snapshots"},
        headers=headers,
    )
    assert response.status_code == 202
    job = client.get(f"/api/v1/imports/{response.json()['id']}", headers=headers).json()
    assert job["status"] == "completed"
    assert job["successful_rows"] == 1
    assert len(client.get("/api/v1/inventory", headers=headers).json()) >= 1
