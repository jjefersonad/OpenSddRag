"""PATCH a project's default_flow (flow-tagging REQ-002/REQ-003).

Unit 1 — `ProjectUpdate` accepts `default_flow` and `update_project` persists it.
Unit 2 — omitting `default_flow` leaves the current value unchanged.

Real isolated test database, per project convention.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.db import project_repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.management_service import SqlManagementService
from opensddrag.models.project import ProjectCreate
from opensddrag.web.schemas import ProjectUpdate


@pytest_asyncio.fixture
async def project():
    slug = f"test-dflow-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


@pytest.mark.asyncio
async def test_update_project_persists_default_flow(project) -> None:
    # schema accepts the new field
    assert ProjectUpdate.model_validate({"default_flow": "websec"}).default_flow == "websec"

    service = SqlManagementService()
    updated = await service.update_project(project.slug, default_flow="websec")
    assert updated["default_flow"] == "websec"

    reread = await service.get_project(project.slug)
    assert reread["default_flow"] == "websec"


@pytest.mark.asyncio
async def test_update_without_default_flow_leaves_it_unchanged(project) -> None:
    service = SqlManagementService()
    await service.update_project(project.slug, default_flow="websec")

    # a second update touching another field must not reset default_flow
    updated = await service.update_project(project.slug, description="changed")
    assert updated["default_flow"] == "websec"
