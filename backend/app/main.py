import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import configure_logging, get_request_id, request_id_middleware
from app.routers import analytics, api, auth, health, imports, master_data, sales

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title=settings.app_name, debug=settings.debug, version="0.1.0")
app.middleware("http")(request_id_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Server-Timing"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id()
    logger.error(
        "Unhandled application exception",
        exc_info=exc,
        extra={"event_name": "unhandled_exception", "status": 500},
    )
    content: dict[str, str] = {
        "code": "internal_error",
        "message": "Internal server error",
    }
    if request_id:
        content["request_id"] = request_id
    return JSONResponse(
        status_code=500,
        content=content,
    )


app.include_router(health.router)
app.include_router(analytics.router, prefix=settings.api_v1_prefix)
app.include_router(master_data.router, prefix=settings.api_v1_prefix)
app.include_router(sales.router, prefix=settings.api_v1_prefix)
app.include_router(api.router, prefix=settings.api_v1_prefix)
app.include_router(imports.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
