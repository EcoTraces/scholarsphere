import logging
import re
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)
CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", str(uuid4()))


def install_error_handling(app: FastAPI, *, max_request_bytes: int) -> None:
    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        supplied = request.headers.get("X-Correlation-ID", "")
        request.state.correlation_id = (
            supplied if CORRELATION_PATTERN.fullmatch(supplied) else str(uuid4())
        )
        content_length = request.headers.get("Content-Length")
        if content_length and content_length.isdigit():
            if int(content_length) > max_request_bytes:
                return _response(
                    request,
                    413,
                    "payload_too_large",
                    "Request payload is too large.",
                )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        message = error.detail if isinstance(error.detail, str) else "Request failed."
        return _response(
            request,
            error.status_code,
            _code_for_status(error.status_code),
            message,
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        fields = [
            {
                "field": ".".join(str(part) for part in item["loc"]),
                "message": item["msg"],
            }
            for item in error.errors()
        ]
        return _response(
            request,
            422,
            "validation_error",
            "Request validation failed.",
            details=fields,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error(
            "unhandled_request_error correlation_id=%s path=%s error_type=%s",
            correlation_id(request),
            request.url.path,
            type(error).__name__,
        )
        return _response(
            request,
            500,
            "internal_error",
            "An internal error occurred.",
        )


def _response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    *,
    details: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error_body: dict[str, object] = {
        "code": code,
        "message": message,
        "correlation_id": correlation_id(request),
    }
    if details:
        error_body["details"] = details
    body: dict[str, object] = {"error": error_body}
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def _code_for_status(status_code: int) -> str:
    return {
        400: "invalid_request",
        401: "unauthenticated",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "external_rate_limited",
        502: "external_api_failure",
        503: "temporarily_unavailable",
    }.get(status_code, "request_failed")
