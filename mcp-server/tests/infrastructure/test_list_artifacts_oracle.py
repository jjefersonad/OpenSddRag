"""Tests for the `list_artifacts` freshness oracle (reduce-token-consumption tier2-1).

Capability: `working-context-content-cache` REQ-008 — `list_artifacts` MUST
return `id` and `updated_at` for every row so a consumer can tell, with one
cheap content-free call, which cached entries are still fresh. The response
stays content-free (no `content`).

Runs against the isolated test database (see `tests/conftest.py`). Each test
gets a uuid-suffixed project that is cleaned up on teardown.
"""

from __future__ import annotations

from uuid import uuid4

import pytest_asyncio

from opensddrag.db import project_repository, repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.pg.tool_executors import list_artifacts
from opensddrag.models.artifact import (
    ArtifactCreate,
    ArtifactStatus,
    ArtifactType,
    ArtifactUpdate,
)
from opensddrag.models.project import ProjectCreate

_ZERO_EMBEDDING = [0.0] * 384


@pytest_asyncio.fixture
async def project():
    """Yield an isolated project; clean up its artifacts + the project row."""
    slug = f"test-oracle-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute(
            "DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),)
        )
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


async def _seed(project_id, name: str) -> None:
    await repository.create_artifact(
        ArtifactCreate(
            project_id=project_id,
            name=name,
            type=ArtifactType.spec,
            content=f"content of {name}",
            status=ArtifactStatus.active,
            metadata={},
        ),
        _ZERO_EMBEDDING,
    )


async def test_list_artifacts_includes_id_and_updated_at(project):
    await _seed(project.id, "oracle-spec-1")

    rows = await list_artifacts({}, project_id=project.id, caller_id="test", conn=None)

    assert len(rows) == 1
    row = rows[0]
    # REQ-008: id + updated_at present for every row …
    assert set(row.keys()) == {"id", "name", "type", "status", "updated_at"}
    assert row["name"] == "oracle-spec-1"
    # … and content-free (the whole point of a cheap oracle call).
    assert "content" not in row


async def test_updated_at_reflects_current_value(project):
    await _seed(project.id, "oracle-spec-2")

    rows = await list_artifacts({}, project_id=project.id, caller_id="test", conn=None)
    artifact = await repository.get_artifact(project.id, "oracle-spec-2")
    # The oracle's updated_at is the artifact's actual updated_at — this is what
    # the cache compares against to decide hit vs. stale.
    assert rows[0]["updated_at"] == artifact.updated_at
    assert rows[0]["id"] == artifact.id


async def test_updated_at_advances_after_edit(project):
    await _seed(project.id, "oracle-spec-3")
    before = (
        await list_artifacts({}, project_id=project.id, caller_id="test", conn=None)
    )[0]["updated_at"]

    # An edit bumps updated_at (repository sets updated_at = NOW()); the oracle
    # must surface the new value so the cache invalidates.
    await repository.update_artifact(
        project.id,
        "oracle-spec-3",
        ArtifactUpdate(status=ArtifactStatus.archived),
    )
    after = (
        await list_artifacts({}, project_id=project.id, caller_id="test", conn=None)
    )[0]["updated_at"]

    assert after > before
