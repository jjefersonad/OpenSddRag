"""Tests for the `test` artifact type (embed-tdd-in-sdd-workflow task-db-1).

Capability: `unified-test-artifact-type` REQ-001 — the `artifacts.type` enum
gains a `test` value, and `create_artifact`/`list_artifacts`/`search_semantic`
accept it, so scenario- and unit-level test artifacts can be created and
queried through the existing MCP tools without a new table or new tools.

REQ-004 — `search_semantic(type="test", ...)` and `list_artifacts(type="test",
...)` return `test` artifacts without error (navigability via existing
infrastructure).

Runs against the isolated test database (see `tests/conftest.py`), per
project convention: integration tests hit a real database, not mocks.
"""

from __future__ import annotations

from uuid import uuid4

import pytest_asyncio

from opensddrag.db import project_repository
from opensddrag.infrastructure.pg.pg_tool_registry import PgToolRegistry
from opensddrag.infrastructure.pg.tool_executors import (
    create_artifact,
    list_artifacts,
    search_semantic,
)
from opensddrag.models.artifact import ArtifactType
from opensddrag.models.project import ProjectCreate


def _registry() -> PgToolRegistry:
    return PgToolRegistry(conn_factory=lambda: None, tool_executors={})


# ─── Schema: the 3 tools' input_schema accept type="test" ──────────────────
#
# multi-flow-foundation (database-schema delta REQ-003): artifacts.type became
# free text — the closed `"enum"` list in the tool schemas was replaced by a
# string description, so every kind (SDD or registered by another flow) is
# accepted. These tests now assert the SDD `test` kind is still valid input
# under the open contract.


def test_search_semantic_schema_accepts_test_type() -> None:
    tool = _registry().get("search_semantic")
    assert tool is not None
    type_prop = tool.input_schema["properties"]["type"]
    assert "enum" not in type_prop, (
        "type must be free text after multi-flow-foundation REQ-003"
    )
    assert type_prop["type"] == "string"


def test_list_artifacts_schema_accepts_test_type() -> None:
    tool = _registry().get("list_artifacts")
    assert tool is not None
    type_prop = tool.input_schema["properties"]["type"]
    assert "enum" not in type_prop
    assert type_prop["type"] == "string"


def test_create_artifact_schema_accepts_test_type() -> None:
    tool = _registry().get("create_artifact")
    assert tool is not None
    type_prop = tool.input_schema["properties"]["type"]
    assert "enum" not in type_prop
    assert type_prop["type"] == "string"


# ─── Model: ArtifactType still carries the SDD kinds as constants ──────────


def test_artifact_type_enum_has_test_member() -> None:
    assert str(ArtifactType("test")) == "test"
    assert ArtifactType.test == "test"
    # Free text stays valid: 'test' is not special-cased, just constant.
    assert str(ArtifactType("doc-discovery")) == "doc-discovery"


# ─── Integration: create + query a `test` artifact end-to-end (real DB) ───


@pytest_asyncio.fixture
async def project():
    slug = f"test-artifact-type-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    from opensddrag.db.connection import get_conn

    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


async def test_create_list_and_search_a_test_artifact(project) -> None:
    create_result = await create_artifact(
        {
            "name": "sample-scenario-test",
            "type": "test",
            "content": "Given a confirmed WHEN/THEN scenario, a test artifact is created.",
            "metadata": {"level": "scenario", "test_status": "pending"},
        },
        project_id=project.id,
        caller_id="test",
        conn=None,
    )
    assert "sample-scenario-test" in create_result
    assert "ArtifactType.test" in create_result or "test" in create_result

    listed = await list_artifacts(
        {"type": "test"}, project_id=project.id, caller_id="test", conn=None
    )
    assert len(listed) == 1
    assert listed[0]["name"] == "sample-scenario-test"
    assert listed[0]["type"] == ArtifactType.test

    found = await search_semantic(
        {"query": "confirmed scenario test artifact", "type": "test"},
        project_id=project.id,
        caller_id="test",
        conn=None,
    )
    assert any(r["name"] == "sample-scenario-test" for r in found)
