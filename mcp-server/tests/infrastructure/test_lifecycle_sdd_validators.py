"""Integration: SDD validators served through the (flow, kind) registry.

sdd-workflow-lifecycle REQ-004/REQ-005 (MODIFIED) + flow-registry REQ-003:

* Unit 1 — `validate_artifact` on `(sdd, spec)` returns `{valid: true}` with
  both sections, and the exact "Spec must have a 'Requirements' section."
  message without them.
* Unit 2 — `validate_artifact` on `(sdd, task)` keeps the test-link check:
  missing link → the mandated message; with a linked unit test → valid.

Real isolated test database.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.db import project_repository, repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.pg.tool_executors import (
    create_artifact,
    validate_artifact,
)
from opensddrag.models.project import ProjectCreate

_MISSING_LINK = (
    'Task must link at least one test artifact '
    '(type="test", level="unit") via an implements relationship, '
    "or set metadata.test_exempt=true with a stated reason."
)


@pytest_asyncio.fixture
async def project():
    slug = f"test-lifecycle2-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


async def _create(project_id, name, kind, content, **extra):
    args = {"name": name, "type": kind, "content": content, **extra}
    await create_artifact(args, project_id=project_id, caller_id="t", conn=None)


async def _artifact_id(project_id, name):
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM artifacts WHERE project_id = %s AND name = %s",
                (str(project_id), name),
            )
            return (await cur.fetchone())[0]


# ── Unit 1: spec validation through the registry ─────────────────────────────


@pytest.mark.asyncio
async def test_sdd_spec_valid_through_registry(project) -> None:
    name = f"sdd-spec-ok-{uuid4().hex[:6]}"
    await _create(
        project.id, name, "spec",
        "# cap Specification\n\n## Purpose\nMeaningful.\n\n## Requirements\n### Requirement: REQ-001 x\nbody",
    )
    result = await validate_artifact(
        {"name": name}, project_id=project.id, caller_id="t", conn=None
    )
    assert result == {"valid": True, "issues": []}


@pytest.mark.asyncio
async def test_sdd_spec_missing_requirements_exact_message(project) -> None:
    name = f"sdd-spec-bad-{uuid4().hex[:6]}"
    await _create(
        project.id, name, "spec",
        "# cap Specification\n\n## Purpose\nMeaningful purpose text.",
    )
    result = await validate_artifact(
        {"name": name}, project_id=project.id, caller_id="t", conn=None
    )
    assert result == {
        "valid": False,
        "issues": ["Spec must have a 'Requirements' section."],
    }


# ── Unit 2: task validation keeps test-link check ────────────────────────────


@pytest.mark.asyncio
async def test_sdd_task_missing_link_reports_exact_message(project) -> None:
    name = f"sdd-task-nolink-{uuid4().hex[:6]}"
    await _create(
        project.id, name, "task",
        "## Goal\nDo the thing.\n\n## Acceptance Criteria\n- [ ] REQ-001: it works.",
    )
    result = await validate_artifact(
        {"name": name}, project_id=project.id, caller_id="t", conn=None
    )
    assert result == {"valid": False, "issues": [_MISSING_LINK]}


@pytest.mark.asyncio
async def test_sdd_task_with_linked_unit_test_is_valid(project) -> None:
    task = f"sdd-task-linked-{uuid4().hex[:6]}"
    unit = f"{task}-unit-1"
    await _create(
        project.id, task, "task",
        "## Goal\nDo the thing.\n\n## Acceptance Criteria\n- [ ] REQ-001: it works.",
    )
    await _create(project.id, unit, "test", "Unit test contract for the thing.")
    task_id = await _artifact_id(project.id, task)
    unit_id = await _artifact_id(project.id, unit)
    await repository.link_artifacts(task_id, unit_id, "implements")

    result = await validate_artifact(
        {"name": task}, project_id=project.id, caller_id="t", conn=None
    )
    assert result == {"valid": True, "issues": []}