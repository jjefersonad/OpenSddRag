"""Route table for the /api/v1 management REST adapter.

`build_routes(service)` aggregates the per-domain routers into the single
list of Starlette `Route`s the SSE-mode app mounts (backend-6). Routes
carry the full `/api/v1/...` paths.
"""

from __future__ import annotations

from starlette.routing import Route

from opensddrag.web.api.artifacts import artifact_routes
from opensddrag.web.api.flows import flows_routes
from opensddrag.web.api.projects import project_routes
from opensddrag.web.api.rules import rule_routes
from opensddrag.web.api.search import search_routes
from opensddrag.web.api.tasks import task_routes
from opensddrag.web.api.traces import trace_routes
from opensddrag.web.service import ManagementServiceProtocol


def build_routes(service: ManagementServiceProtocol) -> list[Route]:
    """Return every /api/v1 route, wired to `service`."""
    return [
        *project_routes(service),
        *artifact_routes(service),
        *flows_routes(service),
        *rule_routes(service),
        *task_routes(service),
        *trace_routes(service),
        *search_routes(service),
    ]


__all__ = ["build_routes"]