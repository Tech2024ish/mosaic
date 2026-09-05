from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.parse import quote_plus

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MOSAIC API"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    db_user: str = "mosaic"
    db_password: str = "mosaic"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "mosaic"
    database_url: str | None = None
    secret_key: str = "development-only-change-me-use-a-longer-local-secret-key"
    access_token_expire_minutes: int = 30
    storage_root: str = ".mosaic-storage"
    max_upload_size_bytes: int = 25_000_000
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout_seconds: int = 30
    backend_cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if self.database_url is None:
            encoded_password = quote_plus(self.db_password)
            self.database_url = (
                f"postgresql+psycopg://{self.db_user}:{encoded_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
