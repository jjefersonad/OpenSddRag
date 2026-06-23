"""Resource query helpers for the MCP resource handlers.

Infrastructure-layer module that mediates between `mcp/server.py` and the
database repositories so that `mcp/server.py` has zero direct `db` imports
(required by the layer-boundary rule in mcp-server-internals-spec REQ-005).
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from opensddrag.db import project_repository, repository


async def list_project_resources() -> list[dict[str, str]]:
    """Return [{uri, name, description}] for every registered project."""
    projects = await project_repository.list_projects()
    return [
        {
            "uri": f"project://{p.slug}",
            "name": f"Project: {p.name}",
            "description": p.description or "",
        }
        for p in projects
    ]


async def read_project_resource(slug: str) -> str:
    project = await project_repository.get_project_by_slug(slug)
    if not project:
        return json.dumps({"error": f"Project '{slug}' not found."})
    artifacts = await repository.list_artifacts(project.id)
    return json.dumps(
        {
            "project": project.model_dump(),
            "artifacts": [
                {"name": a.name, "type": a.type, "status": a.status}
                for a in artifacts
            ],
        },
        default=str,
        indent=2,
    )


async def read_artifact_resource(artifact_id: str) -> str:
    artifact = await repository.get_artifact_by_id(UUID(artifact_id))
    if not artifact:
        return json.dumps({"error": "Artifact not found."})
    return json.dumps(artifact.model_dump(), default=str, indent=2)
