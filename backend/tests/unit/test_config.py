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
