import contextvars
import json
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    return request_id_context.get()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        force=False,
    )


class OperationalFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = get_request_id()
        if request_id:
            payload["request_id"] = request_id
        for field in (
            "organization_id",
            "user_id",
            "import_id",
            "job_id",
            "dataset_type",
            "status",
            "event_name",
            "duration_seconds",
            "failure_category",
            "total_rows",
            "successful_rows",
            "failed_rows",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, default=str)


def valid_request_id(value: str | None) -> str:
    if value and _SAFE_REQUEST_ID.fullmatch(value):
        return value
    return str(uuid.uuid4())


async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = valid_request_id(request.headers.get(REQUEST_ID_HEADER))
    token = request_id_context.set(request_id)
    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        request_id_context.reset(token)
