from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app


def test_import_endpoints_require_authentication() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/imports/00000000-0000-0000-0000-000000000000").status_code == 401
    assert (
        client.get("/api/v1/imports/00000000-0000-0000-0000-000000000000/errors").status_code == 401
    )


def test_import_rejects_non_csv_filename_before_authored_storage() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/imports",
        files={"file": ("payload.txt", BytesIO(b"not csv"), "text/plain")},
        data={"dataset_type": "sales_history"},
    )
    assert response.status_code == 401
