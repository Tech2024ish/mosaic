from fastapi.testclient import TestClient

from app.main import app


def test_import_endpoints_require_authentication() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/imports/00000000-0000-0000-0000-000000000000").status_code == 401
    assert (
        client.get("/api/v1/imports/00000000-0000-0000-0000-000000000000/errors").status_code == 401
    )
