import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_LOGGER_NAME = "app.request"

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
# Client-supplied ids are echoed in a header and in logs: accept only a safe shape.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_EXTRA_FIELDS = ("method", "path", "status_code", "duration_ms")


def get_request_id() -> str | None:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        for field in _EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Send application logs to stdout as one JSON object per line."""
    logger = logging.getLogger("app")
    logger.setLevel(level)
    if not any(getattr(h, "_nubara", False) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler._nubara = True  # type: ignore[attr-defined]
        handler.setFormatter(JsonFormatter())
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)


def _resolve_request_id(request: Request) -> str:
    supplied = request.headers.get(REQUEST_ID_HEADER, "")
    return supplied if _VALID_REQUEST_ID.match(supplied) else uuid.uuid4().hex


def register_request_middleware(app: FastAPI) -> None:
    """Attach the request id, request logging and the safe 500 handler.

    Unexpected errors are caught here, inside the request-id scope, so the
    generic 500 body and the logged details share the same id. Only the path
    is logged (never the query string or body) to keep personal data out.
    """
    request_logger = logging.getLogger(REQUEST_LOGGER_NAME)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = _resolve_request_id(request)
        token = _request_id.set(request_id)
        start = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception:
                request_logger.exception(
                    "unhandled error",
                    extra={"method": request.method, "path": request.url.path},
                )
                response = JSONResponse(
                    status_code=500,
                    content={
                        "detail": "Internal server error",
                        "request_id": request_id,
                    },
                )
            response.headers[REQUEST_ID_HEADER] = request_id
            request_logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                },
            )
            return response
        finally:
            _request_id.reset(token)
