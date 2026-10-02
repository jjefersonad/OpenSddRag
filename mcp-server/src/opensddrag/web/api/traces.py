"""Traces router — /api/v1/projects/{slug}/traces (episodic memory read).

Exposes the project's execution traces (most recent first, `?limit=`).
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.web.deps import require_management_token
from opensddrag.web.errors import error_response, response_for_error
from opensddrag.web.service import ManagementServiceProtocol


def trace_routes(service: ManagementServiceProtocol) -> list[Route]:
    async def list_traces(request: Request) -> JSONResponse:
        raw_limit = request.query_params.get("limit", "20")
        try:
            limit = int(raw_limit)
        except ValueError:
            return error_response(422, "VALIDATION_ERROR", "limit must be an integer")
        if limit < 1:
            return error_response(422, "VALIDATION_ERROR", "limit must be >= 1")
        try:
            return JSONResponse(
                await service.list_traces(request.path_params["slug"], limit)
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    return [
        Route(
            "/api/v1/projects/{slug}/traces",
            require_management_token(list_traces),
            methods=["GET"],
        ),
    ]


__all__ = ["trace_routes"]