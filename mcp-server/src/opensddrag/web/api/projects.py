"""Projects router — /api/v1/projects (project-management REQ-001/002/003)."""

from __future__ import annotations

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.web.deps import require_management_token
from opensddrag.web.errors import error_response, response_for_error, validation_details
from opensddrag.web.schemas import ProjectCreate, ProjectUpdate
from opensddrag.web.service import ManagementServiceProtocol


def _positive_int(raw: str, name: str) -> int | JSONResponse:
    try:
        value = int(raw)
    except ValueError:
        return error_response(422, "VALIDATION_ERROR", f"{name} must be an integer")
    if value < 1:
        return error_response(422, "VALIDATION_ERROR", f"{name} must be >= 1")
    return value


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
            created = await service.create_project(dto.name, dto.slug, dto.description, dto.language)
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(created, status_code=201)

    async def update_project(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return error_response(422, "VALIDATION_ERROR", "request body is not valid JSON")
        try:
            dto = ProjectUpdate.model_validate(payload)
        except ValidationError as exc:
            return error_response(
                422, "VALIDATION_ERROR", "invalid project payload", validation_details(exc)
            )
        try:
            updated = await service.update_project(
                request.path_params["slug"],
                name=dto.name,
                description=dto.description,
                language=dto.language,
                new_slug=dto.slug,
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(updated)

    async def delete_project(request: Request) -> JSONResponse:
        try:
            return JSONResponse(await service.delete_project(request.path_params["slug"]))
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def get_project(request: Request) -> JSONResponse:
        try:
            return JSONResponse(await service.get_project(request.path_params["slug"]))
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def get_session(request: Request) -> JSONResponse:
        try:
            return JSONResponse(await service.get_session(request.path_params["slug"]))
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def get_tree(request: Request) -> JSONResponse:
        try:
            return JSONResponse(await service.get_tree(request.path_params["slug"]))
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def list_changes(request: Request) -> JSONResponse:
        page = _positive_int(request.query_params.get("page", "1"), "page")
        if isinstance(page, JSONResponse):
            return page
        page_size = _positive_int(request.query_params.get("page_size", "8"), "page_size")
        if isinstance(page_size, JSONResponse):
            return page_size
        try:
            return JSONResponse(
                await service.list_changes(
                    request.path_params["slug"], page=page, page_size=page_size
                )
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    async def get_change_bundle(request: Request) -> JSONResponse:
        try:
            return JSONResponse(
                await service.get_change_bundle(
                    request.path_params["slug"],
                    request.path_params["change"],
                )
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)

    return [
        Route("/api/v1/projects", require_management_token(list_projects), methods=["GET"]),
        Route("/api/v1/projects", require_management_token(create_project), methods=["POST"]),
        Route("/api/v1/projects/{slug}", require_management_token(get_project), methods=["GET"]),
        Route("/api/v1/projects/{slug}", require_management_token(update_project), methods=["PATCH"]),
        Route("/api/v1/projects/{slug}", require_management_token(delete_project), methods=["DELETE"]),
        Route(
            "/api/v1/projects/{slug}/session",
            require_management_token(get_session),
            methods=["GET"],
        ),
        Route(
            "/api/v1/projects/{slug}/tree",
            require_management_token(get_tree),
            methods=["GET"],
        ),
        Route(
            "/api/v1/projects/{slug}/changes",
            require_management_token(list_changes),
            methods=["GET"],
        ),
        Route(
            "/api/v1/projects/{slug}/changes/{change}",
            require_management_token(get_change_bundle),
            methods=["GET"],
        ),
    ]


__all__ = ["project_routes"]