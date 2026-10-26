"""Dependencies for the /api/v1 management REST adapter.

Per web-management-system web-api-management delta REQ-002: every
/api/v1 route requires `Authorization: Bearer <MANAGEMENT_API_TOKEN>`;
missing/malformed/mismatched tokens get HTTP 401 with the structured
UNAUTHORIZED envelope (same shape as MCP tool errors). When the server
has no token configured, the API fails closed — every request gets 401
and a startup warning is logged.

Also provides `wire_cors(settings)` so the Starlette app in SSE mode can
allow the configured `web_origin`.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any, Callable, Awaitable

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from opensddrag.config import settings

logger = logging.getLogger(__name__)

_MIME = "application/json"


def _unauthorized(message: str) -> JSONResponse:
    """Build the 401 response in the shared error-envelope shape."""
    return JSONResponse(
        {"error": {"code": "UNAUTHORIZED", "message": message}},
        status_code=401,
        media_type=_MIME,
    )


async def _auth_inner(request: Request) -> JSONResponse | None:
    """Return a 401 JSONResponse when the request is not authorized, else None."""
    expected = getattr(settings, "management_token", None)
    header = request.headers.get("authorization")

    if expected is None or expected == "":
        # Fail closed: no token configured → management API disabled.
        return _unauthorized(
            "Management API is disabled (no MANAGEMENT_API_TOKEN configured)"
        )

    if header is None:
        return _unauthorized("Missing bearer token")

    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return _unauthorized("Authorization header must be 'Bearer <token>'")

    if not secrets.compare_digest(token, expected):
        return _unauthorized("Invalid bearer token")

    return None


def require_management_token(
    endpoint: Callable[[Request], Awaitable[Any]]
) -> Callable[[Request], Awaitable[Any]]:
    """Wrap a route handler with the bearer-token gate (REQ-002).

    The wrapped handler runs ONLY when the Authorization header carries
    the configured management token. Otherwise a 401 envelope is returned
    and the handler body never executes.
    """

    async def guarded(request: Request) -> Any:
        denial = await _auth_inner(request)
        if denial is not None:
            return denial
        return await endpoint(request)

    return guarded


def wire_cors(settings_obj: Any) -> list[Middleware]:
    """Build the CORS middleware stack allowing `settings.web_origin`.

    Kept as a helper so the SSE-mode Starlette assembly (backend-6) can
    include it in `Middleware(...)` lists.
    """
    return [
        Middleware(
            CORSMiddleware,
            allow_origins=[settings_obj.web_origin],
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )
    ]


def warn_if_disabled() -> None:
    """Startup warning per REQ-002: token unset → fail-closed mode announced."""
    if getattr(settings, "management_token", None) is None:
        logger.warning(
            "MANAGEMENT_API_TOKEN is not configured: the /api/v1 management "
            "REST API responds 401 (fails closed) to every request."
        )