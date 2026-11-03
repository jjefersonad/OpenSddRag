"""projects.language — project-management delta REQ-004 (web-ui-design-alignment).

Integration: language captured at creation, optional (empty default),
returned by list/detail. Isolated test DB per project convention.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.db import project_repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.management_service import SqlManagementService
from opensddrag.models.project import ProjectCreate


@pytest_asyncio.fixture
async def project():
    slug = f"test-lang-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


async def test_language_persisted_on_creation(project) -> None:
    """REQ-004 scenario 1: language captured at creation and returned."""
    svc = SqlManagementService()
    created = await svc.create_project(
        "Lang Proj", f"lang-{uuid4().hex[:8]}", "d", "Typescript"
    )
    slug = created["slug"]
    try:
        listed = await svc.list_projects()
        match = next(p for p in listed if p["slug"] == slug)
        assert match["language"] == "Typescript"
        detail = await svc.get_project(slug)
        assert detail["language"] == "Typescript"
    finally:
        import psycopg.rows
        from opensddrag.db.connection import get_conn
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM projects WHERE slug = %s", (slug,))


async def test_language_optional_defaults_empty(project) -> None:
    """REQ-004 scenario 2: creation without language → empty, no error."""
    svc = SqlManagementService()
    created = await svc.create_project(
        "NoLang", f"nolang-{uuid4().hex[:8]}"
    )
    assert created["language"] == ""
    import psycopg.rows
    from opensddrag.db.connection import get_conn
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM projects WHERE slug = %s", (created["slug"],))
