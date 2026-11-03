"""Tests for SDD-world flow tagging (task-lifecycle-1).

sdd-workflow-lifecycle REQ-008 + database-schema REQ-007 (MODIFIED):
the SDD world is `flow='sdd'`.

* Unit 1 — every global SDD skill seeded by `init` has `flow='sdd'` and
  `project_id IS NULL`; explicit non-default flows round-trip through the
  skill repository (so seeds are tagged deliberately, not by accident).
* Unit 2 — every artifact created by an SDD command (proposal, spec,
  design, task) carries `flow='sdd'`, and validation behaviour is
  unchanged.

Integration tests against the real isolated test database.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.db import project_repository, repository, skill_repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.pg.tool_executors import (
    create_artifact,
    validate_artifact,
)
from opensddrag.models.project import ProjectCreate
from opensddrag.models.skill import SkillCreate, SkillStep


@pytest_asyncio.fixture
async def project():
    slug = f"test-lifecycle-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM skills WHERE name LIKE 'test-lifecycle-%'")
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


# ── Unit 1: SDD skills seeded with flow ──────────────────────────────────────


@pytest.mark.asyncio
async def test_seeded_global_skills_have_sdd_flow() -> None:
    """REQ-007: every global SDD skill seeded by init has flow='sdd'."""
    from opensddrag.cli._seeds import seed_sdd_skills

    await seed_sdd_skills()
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT name, flow, project_id FROM skills WHERE project_id IS NULL"
            )
            rows = await cur.fetchall()
    assert rows, "seed_sdd_skills must have seeded global skills"
    bad = [(n, f) for (n, f, _pid) in rows if f != "sdd"]
    assert not bad, f"global SDD skills must carry flow='sdd', offenders: {bad}"


@pytest.mark.asyncio
async def test_skill_repository_round_trips_explicit_flow() -> None:
    """A non-default flow passed to create_skill must persist (not defaulted)."""
    name = f"test-lifecycle-skill-{uuid4().hex[:6]}"
    await skill_repository.create_skill(
        SkillCreate(
            project_id=None,
            name=name,
            description="A docs skill for the lifecycle test.",
            workflow_steps=[SkillStep(step=1, instruction="Do the doc thing.")],
            flow="docs",
        ),
        [0.0] * 384,
    )
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT flow FROM skills WHERE name = %s", (name,))
            row = await cur.fetchone()
    assert row is not None and row[0] == "docs", (
        f"create_skill must persist the explicit flow, got {row}"
    )


# ── Unit 2: SDD artifacts tagged with sdd flow ───────────────────────────────


@pytest.mark.asyncio
async def test_sdd_artifacts_carry_sdd_flow(project) -> None:
    """REQ-008: SDD-created artifacts carry flow='sdd'."""
    kinds = ["proposal", "spec", "design", "task"]
    for kind in kinds:
        content = (
            "## Purpose\nMeaningful.\n\n## Requirements\n### Requirement: REQ-001 x\nbody"
            if kind == "spec"
            else "## Goal\nSomething real.\n\n## Acceptance Criteria\n- [ ] REQ-001 x"
            if kind == "task"
            else f"A {kind} body that is long enough."
        )
        await create_artifact(
            {"name": f"{kind}-{uuid4().hex[:6]}", "type": kind, "content": content},
            project_id=project.id,
            caller_id="t",
            conn=None,
        )
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT DISTINCT flow FROM artifacts WHERE project_id = %s",
                (str(project.id),),
            )
            flows = {r[0] for r in await cur.fetchall()}
    assert flows == {"sdd"}, f"SDD artifacts must all be flow='sdd', got {flows}"


@pytest.mark.asyncio
async def test_sdd_spec_validation_unchanged(project) -> None:
    """Regression: the built-in (sdd, spec) validator still applies."""
    name = f"sdd-spec-{uuid4().hex[:6]}"
    await create_artifact(
        {
            "name": name,
            "type": "spec",
            "content": "# cap Specification\n\n## Purpose\nMeaningful purpose here.",
        },
        project_id=project.id,
        caller_id="t",
        conn=None,
    )
    result = await validate_artifact(
        {"name": name}, project_id=project.id, caller_id="t", conn=None
    )
    assert result == {
        "valid": False,
        "issues": ["Spec must have a 'Requirements' section."],
    }