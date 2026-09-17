from typing import Any, cast

from app.core.config import Settings


def test_origins_are_parsed_from_environment_style_string() -> None:
    settings = Settings(
        backend_cors_origins=cast(Any, "http://localhost:5173, https://example.com")
    )
    assert settings.backend_cors_origins == ["http://localhost:5173", "https://example.com"]


def test_production_rejects_development_secret() -> None:
    try:
        Settings(environment="production", debug=False, secret_key="development-only-secret")
    except ValueError as exc:
        assert "production secret_key" in str(exc)
    else:
        raise AssertionError("production settings accepted a development secret")


def test_production_rejects_default_database_password() -> None:
    try:
        Settings(
            environment="production",
            debug=False,
            secret_key="a" * 64,
            db_password="mosaic",
            database_url="",
            backend_cors_origins=["https://app.example.com"],
        )
    except ValueError as exc:
        assert "database password" in str(exc)
    else:
        raise AssertionError("production settings accepted the default database password")


def test_production_rejects_localhost_cors() -> None:
    try:
        Settings(
            environment="production",
            debug=False,
            secret_key="a" * 64,
            db_password="not-default",
            database_url="postgresql+psycopg://mosaic:db-password@db:5432/mosaic",
            backend_cors_origins=["http://localhost:5173"],
        )
    except ValueError as exc:
        assert "CORS" in str(exc)
    else:
        raise AssertionError("production settings accepted a localhost CORS origin")
