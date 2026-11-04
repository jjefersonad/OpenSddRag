"""GET /projects/{slug}/changes?status=all|live (dashboard-flows REQ-003/REQ-004).

Unit 1 — `status=all` includes archived/non-live changes with their last stage.
Unit 2 — the default (no status) keeps returning only live changes.

Real isolated test database, per project convention.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.db import project_repository, repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.management_service import SqlManagementService
from opensddrag.models.artifact import ArtifactCreate
from opensddrag.models.project import ProjectCreate

_ZERO = [0.0] * 384


@pytest_asyncio.fixture
async def project():
    slug = f"test-chst-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


async def _seed(project, name: str, change: str, status: str) -> None:
    await repository.create_artifact(
        ArtifactCreate(
            project_id=project.id,
            name=name,
            type="proposal",
            content="x" * 20,
            status=status,
            flow="sdd",
            metadata={"change_name": change},
        ),
        _ZERO,
    )


@pytest.mark.asyncio
async def test_status_all_includes_archived_changes(project) -> None:
    await _seed(project, "live-1", "live-chg", "active")
    await _seed(project, "arch-1", "arch-chg", "archived")

    svc = SqlManagementService()
    live = await svc.list_changes(project.slug, 1, 50)
    allc = await svc.list_changes(project.slug, 1, 50, status="all")

    live_names = {c["change"] for c in live["items"]}
    all_names = {c["change"] for c in allc["items"]}
    assert "live-chg" in live_names
    assert "arch-chg" not in live_names
    assert {"live-chg", "arch-chg"} <= all_names
    # each change carries its last reached stage
    assert all(isinstance(c["phases"], list) for c in allc["items"])


@pytest.mark.asyncio
async def test_default_status_is_live(project) -> None:
    await _seed(project, "live-1", "live-chg", "active")
    await _seed(project, "arch-1", "arch-chg", "archived")

    svc = SqlManagementService()
    default = await svc.list_changes(project.slug, 1, 50)
    live = await svc.list_changes(project.slug, 1, 50, status="live")

    default_names = {c["change"] for c in default["items"]}
    assert default_names == {c["change"] for c in live["items"]}
    assert "arch-chg" not in default_names
