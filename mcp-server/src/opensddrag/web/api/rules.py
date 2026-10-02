"""Rules router — /api/v1/projects/{slug}/rules.

GET list (harness-rules-management REQ-001), POST create with enum
validation (REQ-002), PATCH {enabled} soft-delete/restore (REQ-003 /
web-api-management REQ-006).
"""

from __future__ import annotations

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.web.deps import require_management_token
from opensddrag.web.errors import error_response, response_for_error, validation_details
from opensddrag.web.schemas import RuleCreate, RuleToggle
from opensddrag.web.service import ManagementServiceProtocol




def rule_routes(service: ManagementServiceProtocol) -> list[Route]:
    async def list_rules(request: Request) -> JSONResponse:
        enabled_all = request.query_params.get("enabled_all", "").lower() == "true"
        try:
            return JSONResponse(
                await service.list_rules(request.path_params["slug"], enabled_all)
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def create_rule(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return error_response(422, "VALIDATION_ERROR", "request body is not valid JSON")
        try:
            dto = RuleCreate.model_validate(payload)
        except ValidationError as exc:
            return error_response(422, "VALIDATION_ERROR", "invalid rule payload", validation_details(exc))
        try:
            created = await service.create_rule(
                request.path_params["slug"],
                dto.name,
                dto.trigger,
                dto.category,
                dto.severity,
                dto.instruction,
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(created, status_code=201)

    async def patch_rule(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return error_response(422, "VALIDATION_ERROR", "request body is not valid JSON")
        try:
            dto = RuleToggle.model_validate(payload)
        except ValidationError as exc:
            return error_response(422, "VALIDATION_ERROR", "invalid rule payload", validation_details(exc))
        try:
            updated = await service.set_rule_enabled(
                request.path_params["slug"], request.path_params["rule_id"], dto.enabled
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(updated)

    return [
        Route(
            "/api/v1/projects/{slug}/rules",
            require_management_token(list_rules),
            methods=["GET"],
        ),
        Route(
            "/api/v1/projects/{slug}/rules",
            require_management_token(create_rule),
            methods=["POST"],
        ),
        Route(
            "/api/v1/projects/{slug}/rules/{rule_id}",
            require_management_token(patch_rule),
            methods=["PATCH"],
        ),
    ]


__all__ = ["rule_routes"]