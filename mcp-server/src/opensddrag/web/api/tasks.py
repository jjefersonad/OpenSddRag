"""Tasks router — /api/v1/projects/{slug}/tasks/{id}.

PATCH `{done}` sets/merges `metadata.done` on the task artifact
(web-api-management REQ-004). Tasks belonging to another project → 404.
"""

from __future__ import annotations

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.web.deps import require_management_token
from opensddrag.web.errors import error_response, response_for_error, validation_details
from opensddrag.web.schemas import TaskUpdate
from opensddrag.web.service import ManagementServiceProtocol


def task_routes(service: ManagementServiceProtocol) -> list[Route]:
    async def patch_task(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return error_response(422, "VALIDATION_ERROR", "request body is not valid JSON")
        try:
            dto = TaskUpdate.model_validate(payload)
        except ValidationError as exc:
            return error_response(
                422,
                "VALIDATION_ERROR",
                "invalid task payload",
                [{"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()],
            )
        try:
            updated = await service.set_task_done(
                request.path_params["slug"], request.path_params["task_id"], dto.done
            )
        except Exception as exc:  # noqa: BLE001
            return response_for_error(exc)
        return JSONResponse(updated)

    return [
        Route(
            "/api/v1/projects/{slug}/tasks/{task_id}",
            require_management_token(patch_task),
            methods=["PATCH"],
        ),
    ]


__all__ = ["task_routes"]