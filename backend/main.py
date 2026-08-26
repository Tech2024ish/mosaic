"""Developer-friendly Uvicorn entrypoint for commands run from ``backend/``."""

from app.main import app

__all__ = ["app"]
