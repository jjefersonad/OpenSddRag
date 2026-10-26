"""SqlManagementService API-key management (dashboard keys page)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from opensddrag.core.domain.errors import ResourceNotFoundError
from opensddrag.db import api_key_repository, project_repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.management_service import SqlManagementService
from opensddrag.models.project import ProjectCreate


def _svc() -> SqlManagementService:
    return SqlManagementService()


@pytest.mark.asyncio
async def test_create_list_revoke_api_key_roundtrip():
    suffix = uuid4().hex[:8]
    project = await project_repository.create_project(
        ProjectCreate(slug=f"keys-web-{suffix}", name=f"keys-web-{suffix}")
    )
    svc = _svc()
    try:
        created = await svc.create_api_key("dashboard test", project.slug, None)
        assert created["key"]
        assert created["prefix"] == created["key"][:8]
        assert created["project_slug"] == project.slug
        assert created["status"] == "active"
        assert "key_hash" not in created

        listed = await svc.list_api_keys(project.slug, include_revoked=False)
        assert [k["id"] for k in listed] == [created["id"]]
        assert "key" not in listed[0]
        assert "key_hash" not in listed[0]

        hidden = await api_key_repository.lookup_by_hash(created["key"])
        assert hidden is not None

        revoked = await svc.revoke_api_key(created["id"])
        assert revoked["status"] == "revoked"
        assert await api_key_repository.lookup_by_hash(created["key"]) is not None
        after = await svc.list_api_keys(project.slug, include_revoked=False)
        assert after == []
    finally:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM projects WHERE id = %s", (str(project.id),))


@pytest.mark.asyncio
async def test_create_api_key_unknown_project_404():
    with pytest.raises(ResourceNotFoundError):
        await _svc().create_api_key("x", "does-not-exist")


@pytest.mark.asyncio
async def test_revoke_unknown_key_404():
    with pytest.raises(ResourceNotFoundError):
        await _svc().revoke_api_key("00000000-0000-0000-0000-000000000000")
