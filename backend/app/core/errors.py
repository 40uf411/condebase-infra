from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

DEFAULT_ERROR_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "PAYLOAD_TOO_LARGE",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "UNSUPPORTED_MEDIA_TYPE",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
    status.HTTP_502_BAD_GATEWAY: "BAD_GATEWAY",
    status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
}


def default_error_code(status_code: int) -> str:
    code = DEFAULT_ERROR_CODES.get(status_code)
    if code:
        return code
    return f"HTTP_{status_code}"


def _http_status_phrase(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Request failed"


def _normalize_validation_issues(raw_errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for item in raw_errors:
        location = item.get("loc", ())
        if isinstance(location, tuple):
            field = ".".join(str(segment) for segment in location)
        elif isinstance(location, list):
            field = ".".join(str(segment) for segment in location)
        else:
            field = str(location)

        issues.append(
            {
                "field": field,
                "message": str(item.get("msg", "Invalid value")),
                "type": str(item.get("type", "validation_error")),
            }
        )
    return issues


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str | None = None,
    message: str | None = None,
    details: dict[str, Any] | list[Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    payload = {
        "error": {
            "code": code or default_error_code(status_code),
            "message": message or _http_status_phrase(status_code),
            "details": details,
            "status": status_code,
            "requestId": request_id,
        }
    }
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    status_code = int(exc.status_code)
    detail = exc.detail

    code: str | None = None
    message: str | None = None
    details: dict[str, Any] | list[Any] | None = None

    if isinstance(detail, str):
        message = detail
    elif isinstance(detail, dict):
        maybe_code = detail.get("code")
        maybe_message = detail.get("message")
        code = str(maybe_code).strip() if maybe_code is not None else None
        message = str(maybe_message).strip() if maybe_message is not None else None
        details = detail.get("details") if "details" in detail else detail
    elif isinstance(detail, list):
        details = detail

    return error_response(
        request,
        status_code=status_code,
        code=code or default_error_code(status_code),
        message=message or _http_status_phrase(status_code),
        details=details,
        headers=exc.headers,
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    issues = _normalize_validation_issues(exc.errors())
    return error_response(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"issues": issues},
    )


async def unhandled_exception_handler(request: Request, _: Exception) -> JSONResponse:
    return error_response(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
    )
