from fastapi import APIRouter
from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.database.session import check_database_connection
from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        check_database_connection()
    except SQLAlchemyError:
        return HealthResponse(status="degraded", database="unavailable")
    return HealthResponse(status="ok", database="ok")


@router.get("/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    try:
        check_database_connection()
    except SQLAlchemyError:
        return HealthResponse(status="not_ready", database="unavailable")
    return HealthResponse(status="ready", database="ok")
