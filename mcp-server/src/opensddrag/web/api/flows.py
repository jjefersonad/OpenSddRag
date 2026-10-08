"""Flows router — GET /api/v1/flows (web-apiManagement delta REQ-008).

Exposes the flow registry (flows + artifact_kinds) so the UI can render
any registered workflow's kinds and lifecycle without SDD assumptions
(design D6/D7).
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.web.deps import require_management_token
from opensddrag.web.errors import response_for_error
from opensddrag.web.service import ManagementServiceProtocol


def flows_routes(service: ManagementServiceProtocol) -> list[Route]:
    async def list_flows(request: Request) -> JSONResponse:
        try:
            return JSONResponse(await service.list_flows())
        except Exception as exc:  # noqa: BLE001 - mapped to envelope
            return response_for_error(exc)

    return [Route("/api/v1/flows", require_management_token(list_flows), methods=["GET"])]


__all__ = ["flows_routes"]