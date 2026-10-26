"""API keys router — /api/v1/keys.

Management-token CRUD for MCP Bearer keys. List never returns the
plaintext or hash; POST create includes `key` once.
"""

from __future__ import annotations

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.web.deps import require_management_token
from opensddrag.web.errors import error_response, response_for_error, validation_details
from opensddrag.web.schemas import ApiKeyCreate
from opensddrag.web.service import ManagementServiceProtocol


def key_routes(service: ManagementServiceProtocol) -> list[Route]:
    async def list_keys(request: Request) -> JSONResponse:
        include_revoked = request.query_params.get("include_revoked", "").lower() == "true"
        project_slug = request.query_params.get("project") or None
        scope = request.query_params.get("scope") or None
        try:
            return JSONResponse(
                await service.list_api_keys(project_slug, include_revoked, scope)
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def create_key(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return error_response(422, "VALIDATION_ERROR", "request body is not valid JSON")
        try:
            dto = ApiKeyCreate.model_validate(payload)
        except ValidationError as exc:
            return error_response(
                422, "VALIDATION_ERROR", "invalid api key payload", validation_details(exc)
            )
        try:
            created = await service.create_api_key(
                dto.description, dto.project_slug, dto.expires_at
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(created, status_code=201)

    async def revoke_key(request: Request) -> JSONResponse:
        try:
            updated = await service.revoke_api_key(request.path_params["key_id"])
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(updated)

    return [
        Route("/api/v1/keys", require_management_token(list_keys), methods=["GET"]),
        Route("/api/v1/keys", require_management_token(create_key), methods=["POST"]),
        Route(
            "/api/v1/keys/{key_id}/revoke",
            require_management_token(revoke_key),
            methods=["POST"],
        ),
    ]


__all__ = ["key_routes"]
