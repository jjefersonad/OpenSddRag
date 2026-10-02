"""Projects router — /api/v1/projects (project-management REQ-001/002/003)."""

from __future__ import annotations

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.web.deps import require_management_token
from opensddrag.web.errors import error_response, response_for_error, validation_details
from opensddrag.web.schemas import ProjectCreate
from opensddrag.web.service import ManagementServiceProtocol




def project_routes(service: ManagementServiceProtocol) -> list[Route]:
    async def list_projects(request: Request) -> JSONResponse:
        try:
            return JSONResponse(await service.list_projects())
        except Exception as exc:  # noqa: BLE001 - mapped to envelope
            return response_for_error(exc)

    async def create_project(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001 - malformed JSON body
            return error_response(422, "VALIDATION_ERROR", "request body is not valid JSON")
        try:
            dto = ProjectCreate.model_validate(payload)
        except ValidationError as exc:
            return error_response(
                422, "VALIDATION_ERROR", "invalid project payload", validation_details(exc)
            )
        try:
            created = await service.create_project(dto.name, dto.slug, dto.description)
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(created, status_code=201)

    async def get_project(request: Request) -> JSONResponse:
        try:
            return JSONResponse(await service.get_project(request.path_params["slug"]))
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    return [
        Route("/api/v1/projects", require_management_token(list_projects), methods=["GET"]),
        Route("/api/v1/projects", require_management_token(create_project), methods=["POST"]),
        Route("/api/v1/projects/{slug}", require_management_token(get_project), methods=["GET"]),
    ]


__all__ = ["project_routes"]