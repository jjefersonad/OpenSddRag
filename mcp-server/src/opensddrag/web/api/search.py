"""Search router — /api/v1/search (web-api-management REQ-005).

`?q=` is required (missing → 422); `?limit=` defaults to 5. Results are
ordered by descending relevance and shaped for the frontend index:
`{type, title, snippet, project, score, slug}`.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.web.deps import require_management_token
from opensddrag.web.errors import error_response, response_for_error
from opensddrag.web.service import ManagementServiceProtocol


def search_routes(service: ManagementServiceProtocol) -> list[Route]:
    async def search(request: Request) -> JSONResponse:
        query = request.query_params.get("q")
        if query is None or not query.strip():
            return error_response(422, "VALIDATION_ERROR", "query parameter 'q' is required")

        raw_limit = request.query_params.get("limit", "5")
        try:
            limit = int(raw_limit)
        except ValueError:
            return error_response(422, "VALIDATION_ERROR", "limit must be an integer")
        if limit < 1:
            return error_response(422, "VALIDATION_ERROR", "limit must be >= 1")

        try:
            return JSONResponse(await service.search(query, limit))
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    return [
        Route("/api/v1/search", require_management_token(search), methods=["GET"]),
    ]


__all__ = ["search_routes"]