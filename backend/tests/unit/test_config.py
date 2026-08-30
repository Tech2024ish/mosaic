from typing import Any, cast

from app.core.config import Settings


def test_origins_are_parsed_from_environment_style_string() -> None:
    settings = Settings(
        backend_cors_origins=cast(Any, "http://localhost:5173, https://example.com")
    )
    assert settings.backend_cors_origins == ["http://localhost:5173", "https://example.com"]
