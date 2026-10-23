"""SqlManagementService.list_artifacts include_content opt-in
(web-ui-prototype-fidelity backend-2, web-api REQ-013). Isolated test DB."""

from __future__ import annotations

from uuid import uuid4

import pytest_asyncio

from opensddrag.db import project_repository, repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.management_service import SqlManagementService
from opensddrag.models.artifact import ArtifactCreate
from opensddrag.models.project import ProjectCreate


@pytest_asyncio.fixture
async def project():
    slug = f"test-content-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    for i in range(2):
        await repository.create_artifact(
            ArtifactCreate(project_id=proj.id, name=f"c-spec-{i}", type="spec", content=f"# body {i}"),
            embedding=[0.1] * 384,
        )
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


async def test_include_content_returns_bodies(project) -> None:
    items = await SqlManagementService().list_artifacts(project.slug, "spec", include_content=True)
    assert {i["content"] for i in items} == {"# body 0", "# body 1"}


async def test_default_list_has_no_content(project) -> None:
    items = await SqlManagementService().list_artifacts(project.slug, "spec")
    assert len(items) == 2
    assert all("content" not in i for i in items)


async def test_single_read_still_returns_content(project) -> None:
    svc = SqlManagementService()
    first = (await svc.list_artifacts(project.slug, "spec"))[0]
    full = await svc.get_artifact(first["id"])
    assert full["content"].startswith("# body")
