"""Service contract the /api/v1 routers depend on.

`web/service.py` declares the async interface (a `typing.Protocol`) that
the REST delivery adapter consumes. The concrete implementation lives in
`infrastructure/management_service.py` (`SqlManagementService`) and is
injected by the composition/mount layer — this keeps `web/` free of any
`opensddrag.db` import (enforced by
`tests/architecture/test_imports.py::test_web_adapter_does_not_import_repositories`).

Every method returns JSON-serializable primitives (dicts/lists), so
routers can hand them straight to Starlette's `JSONResponse`. Failures
are signalled with the `core.domain.errors` exceptions.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ManagementServiceProtocol(Protocol):
    """Read/write operations backing the management REST API."""

    async def list_projects(self) -> list[dict[str, Any]]: ...

    async def create_project(
        self, name: str, slug: str, description: str = "", language: str = ""
    ) -> dict[str, Any]: ...

    async def get_project(self, slug: str) -> dict[str, Any]: ...

    async def list_artifacts(
        self, slug: str, type_filter: str | None = None, flow_filter: str | None = None
    ) -> list[dict[str, Any]]: ...

    async def get_artifact(self, artifact_id: str) -> dict[str, Any]: ...

    async def get_validation(self, artifact_id: str) -> dict[str, Any]: ...

    async def get_relationships(self, artifact_id: str) -> list[dict[str, Any]]: ...

    async def list_flows(self) -> list[dict[str, Any]]: ...

    async def get_session(self, slug: str) -> dict[str, Any]: ...

    async def get_tree(self, slug: str) -> dict[str, Any]: ...

    async def list_changes(self, slug: str) -> list[dict[str, Any]]: ...

    async def list_rules(
        self, slug: str, enabled_all: bool = False
    ) -> list[dict[str, Any]]: ...

    async def list_traces(
        self, slug: str, limit: int = 20
    ) -> list[dict[str, Any]]: ...

    async def search(
        self, query: str, limit: int = 5
    ) -> list[dict[str, Any]]: ...

    # ── mutations ──
    async def set_task_done(
        self, slug: str, task_id: str, done: bool
    ) -> dict[str, Any]: ...

    async def create_rule(
        self,
        slug: str,
        name: str,
        trigger: str,
        category: str,
        severity: str,
        instruction: str,
    ) -> dict[str, Any]: ...

    async def set_rule_enabled(
        self, slug: str, rule_id: str, enabled: bool
    ) -> dict[str, Any]: ...

    async def create_artifact(
        self,
        slug: str,
        name: str,
        type_filter: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def update_artifact(
        self,
        artifact_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> dict[str, Any]: ...

    async def link_artifact(
        self,
        artifact_id: str,
        relationship_type: str,
        target_name: str | None = None,
        target_id: str | None = None,
    ) -> dict[str, Any]: ...


__all__ = ["ManagementServiceProtocol"]