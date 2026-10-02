"""HTTP error helpers for the /api/v1 management REST adapter.

Every failure returned to a client uses the shared envelope from
`web.schemas.ErrorEnvelope` — the same `{"error": {"code", "message",
"details"?}}` shape the MCP adapter emits for tool errors.
"""

from __future__ import annotations

from typing import Any

from starlette.responses import JSONResponse

from opensddrag.core.domain.errors import (
    ManagementServiceError,
    ResourceConflictError,
    ResourceNotFoundError,
    ManagementValidationError,
)

_STATUS_BY_ERROR = {
    ResourceNotFoundError: 404,
    ResourceConflictError: 409,
    ManagementValidationError: 422,
}
_CODE_BY_ERROR = {
    ResourceNotFoundError: "NOT_FOUND",
    ResourceConflictError: "CONFLICT",
    ManagementValidationError: "VALIDATION_ERROR",
}


def error_response(
    status: int, code: str, message: str, details: Any = None
) -> JSONResponse:
    body: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse({"error": body}, status_code=status)


def response_for_error(exc: Exception) -> JSONResponse:
    """Map a management-service (or unexpected) exception to an HTTP response."""
    for exc_type, status in _STATUS_BY_ERROR.items():
        if isinstance(exc, exc_type):
            return error_response(
                status,
                _CODE_BY_ERROR[exc_type],
                str(getattr(exc, "message", str(exc))),
                getattr(exc, "details", None),
            )
    if isinstance(exc, ManagementServiceError):
        return error_response(500, "INTERNAL", str(exc.message), exc.details)
    return error_response(500, "INTERNAL", "internal server error")


def validation_details(exc: Any) -> list[dict[str, Any]]:
    """JSON-safe projection of a pydantic `ValidationError`'s errors()."""
    return [
        {"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")}
        for e in exc.errors()
    ]


__all__ = ["error_response", "response_for_error", "validation_details"]