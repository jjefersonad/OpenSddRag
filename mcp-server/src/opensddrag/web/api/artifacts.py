"""Artifacts router — /api/v1/.../artifacts and /api/v1/artifacts/{id}.

Reads: list by project (?type=) + single read (artifact-management
REQ-001/002). Writes: create (REQ-003), update (REQ-004), relationships
(REQ-005).
"""

from __future__ import annotations

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.web.deps import require_management_token
from opensddrag.web.errors import error_response, response_for_error, validation_details
from opensddrag.web.schemas import ArtifactCreate, ArtifactUpdate, RelationshipCreate
from opensddrag.web.service import ManagementServiceProtocol




def artifact_routes(service: ManagementServiceProtocol) -> list[Route]:
    async def list_artifacts(request: Request) -> JSONResponse:
        type_filter = request.query_params.get("type")
        try:
            return JSONResponse(
                await service.list_artifacts(request.path_params["slug"], type_filter)
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def create_artifact(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return error_response(422, "VALIDATION_ERROR", "request body is not valid JSON")
        try:
            dto = ArtifactCreate.model_validate(payload)
        except ValidationError as exc:
            return error_response(422, "VALIDATION_ERROR", "invalid artifact payload", validation_details(exc))
        try:
            created = await service.create_artifact(
                request.path_params["slug"],
                dto.name,
                dto.type,
                dto.content,
                dto.metadata,
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(created, status_code=201)

    async def get_artifact(request: Request) -> JSONResponse:
        try:
            return JSONResponse(
                await service.get_artifact(request.path_params["artifact_id"])
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def get_validation(request: Request) -> JSONResponse:
        try:
            return JSONResponse(
                await service.get_validation(request.path_params["artifact_id"])
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def get_relationships(request: Request) -> JSONResponse:
        try:
            return JSONResponse(
                await service.get_relationships(request.path_params["artifact_id"])
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def update_artifact(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return error_response(422, "VALIDATION_ERROR", "request body is not valid JSON")
        try:
            dto = ArtifactUpdate.model_validate(payload)
        except ValidationError as exc:
            return error_response(422, "VALIDATION_ERROR", "invalid artifact payload", validation_details(exc))
        try:
            updated = await service.update_artifact(
                request.path_params["artifact_id"],
                dto.content,
                dto.metadata,
                dto.status,
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(updated)

    async def link_artifact(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return error_response(422, "VALIDATION_ERROR", "request body is not valid JSON")
        try:
            dto = RelationshipCreate.model_validate(payload)
        except ValidationError as exc:
            return error_response(422, "VALIDATION_ERROR", "invalid relationship payload", validation_details(exc))
        try:
            link = await service.link_artifact(
                request.path_params["artifact_id"],
                dto.relationship_type,
                dto.target_name,
                dto.target_id,
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(link, status_code=201)

    return [
        Route(
            "/api/v1/projects/{slug}/artifacts",
            require_management_token(list_artifacts),
            methods=["GET"],
        ),
        Route(
            "/api/v1/projects/{slug}/artifacts",
            require_management_token(create_artifact),
            methods=["POST"],
        ),
        Route(
            "/api/v1/artifacts/{artifact_id}",
            require_management_token(get_artifact),
            methods=["GET"],
        ),
        Route(
            "/api/v1/artifacts/{artifact_id}",
            require_management_token(update_artifact),
            methods=["PATCH"],
        ),
        Route(
            "/api/v1/artifacts/{artifact_id}/validation",
            require_management_token(get_validation),
            methods=["GET"],
        ),
        Route(
            "/api/v1/artifacts/{artifact_id}/relationships",
            require_management_token(get_relationships),
            methods=["GET"],
        ),
        Route(
            "/api/v1/artifacts/{artifact_id}/relationships",
            require_management_token(link_artifact),
            methods=["POST"],
        ),
    ]


__all__ = ["artifact_routes"]