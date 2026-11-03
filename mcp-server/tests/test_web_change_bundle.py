"""Integration tests: SqlManagementService.get_change_bundle (web-change-reader).

Spec refs:
    - web-api-management REQ-014 (change bundle with task bodies)
    - design D1/D2/D7
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.core.domain.errors import ResourceNotFoundError
from opensddrag.db import project_repository, repository
from opensddrag.db.connection import get_conn
from opensddrag.db.flow_registry import register_flow
from opensddrag.infrastructure.management_service import SqlManagementService
from opensddrag.models.artifact import ArtifactCreate
from opensddrag.models.project import ProjectCreate

FLOW = "sddbundle"


def _svc() -> SqlManagementService:
    return SqlManagementService()


async def _register_flow() -> None:
    await register_flow(
        {
            "flow": FLOW,
            "kinds": [{"kind": k} for k in ("proposal", "spec", "design", "task", "test")],
            "harness_triggers": ["on_spec"],
            "lifecycle": [{"name": "Propose", "kinds": ["proposal"]}],
            "commands": [{"name": "propose"}],
            "claude_md_section": "## OpenSddRag — bundle\nx",
        }
    )


async def _mk(proj, name: str, kind: str, status: str = "draft", content: str | None = None, **meta):
    return await repository.create_artifact(
        ArtifactCreate(
            project_id=proj.id,
            name=name,
            type=kind,
            content=content if content is not None else f"# {name}\n\nbody of {name}",
            metadata=meta,
            flow=FLOW,
            status=status,
        ),
        embedding=[0.1] * 384,
    )


async def _drop(*projects) -> None:
    async with get_conn() as conn:
        for p in projects:
            await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(p.id),))
            await conn.execute("DELETE FROM projects WHERE id = %s", (str(p.id),))


@pytest_asyncio.fixture
async def project():
    await _register_flow()
    slug = f"test-bundle-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(
        ProjectCreate(slug=slug, name=slug, description="d", language="Python")
    )
    yield proj
    await _drop(proj)


async def _seed_full_change(project, change: str = "chg-a") -> None:
    await _mk(project, f"{change}-proposal", "proposal", content="# P\n\n## Why\nwhy-a", change_name=change)
    await _mk(project, f"{change}-alpha-spec", "spec", content="# Alpha\n\nalpha-body", change_name=change)
    await _mk(project, f"{change}-beta-spec", "spec", content="# Beta\n\nbeta-body", change_name=change)
    await _mk(project, f"{change}-design", "design", content="# D\n\n## Context\nctx-a", change_name=change)
    await _mk(project, f"{change}-task-1", "task", "archived", content="## Goal\ng1", change_name=change)
    await _mk(project, f"{change}-task-2", "task", "archived", content="## Goal\ng2", change_name=change)
    await _mk(project, f"{change}-task-3", "task", "archived", content="## Goal\ng3", change_name=change)
    await _mk(project, f"{change}-task-4", "task", content="## Goal\ng4", change_name=change, done=False)


# ── unit-1: bodies + task_count ──────────────────────────────────────────────


async def test_get_change_bundle_includes_bodies_and_task_count(project) -> None:
    await _seed_full_change(project)
    bundle = await _svc().get_change_bundle(project.slug, "chg-a")
    assert bundle["change"] == "chg-a"
    assert bundle["flow"] == FLOW
    assert bundle["proposal"]["content"] == "# P\n\n## Why\nwhy-a"
    assert bundle["design"]["content"] == "# D\n\n## Context\nctx-a"
    spec_bodies = {s["name"]: s["content"] for s in bundle["specs"]}
    assert spec_bodies[f"chg-a-alpha-spec"] == "# Alpha\n\nalpha-body"
    assert spec_bodies[f"chg-a-beta-spec"] == "# Beta\n\nbeta-body"
    assert len(bundle["specs"]) == 2
    assert bundle["task_count"] == 4
    assert bundle["task_count"] == len(bundle["tasks"])
    by_name = {t["name"]: t for t in bundle["tasks"]}
    for i in range(1, 5):
        task = by_name[f"chg-a-task-{i}"]
        assert "content" in task and task["content"]
        assert set(task) == {"name", "status", "content", "done"}


# ── unit-2: other change_name excluded ───────────────────────────────────────


async def test_get_change_bundle_excludes_other_changes(project) -> None:
    await _seed_full_change(project, "chg-a")
    await _mk(project, "other-proposal", "proposal", content="# other", change_name="other-chg")
    await _mk(project, "other-task", "task", content="## Goal\nother", change_name="other-chg")
    bundle = await _svc().get_change_bundle(project.slug, "chg-a")
    names = {bundle["proposal"]["name"], bundle["design"]["name"]}
    names.update(s["name"] for s in bundle["specs"])
    names.update(t["name"] for t in bundle["tasks"])
    assert all("other" not in n for n in names)
    assert bundle["task_count"] == 4


# ── unit-3: archived tasks done ──────────────────────────────────────────────


async def test_get_change_bundle_marks_archived_tasks_done(project) -> None:
    await _seed_full_change(project)
    await _mk(
        project,
        "chg-a-task-done-flag",
        "task",
        content="## Goal\nflagged",
        change_name="chg-a",
        done=True,
    )
    bundle = await _svc().get_change_bundle(project.slug, "chg-a")
    by_name = {t["name"]: t for t in bundle["tasks"]}
    assert by_name["chg-a-task-1"]["done"] is True
    assert by_name["chg-a-task-2"]["done"] is True
    assert by_name["chg-a-task-3"]["done"] is True
    assert by_name["chg-a-task-4"]["status"] == "draft"
    assert by_name["chg-a-task-4"]["done"] is False
    assert by_name["chg-a-task-done-flag"]["done"] is True
    assert bundle["task_count"] == 5


# ── unit-4: missing design is null ───────────────────────────────────────────


async def test_get_change_bundle_missing_design_is_null(project) -> None:
    await _mk(project, "solo-proposal", "proposal", content="# P", change_name="solo")
    await _mk(project, "solo-spec", "spec", content="# S", change_name="solo")
    bundle = await _svc().get_change_bundle(project.slug, "solo")
    assert bundle["design"] is None
    assert bundle["proposal"]["content"] == "# P"
    assert len(bundle["specs"]) == 1
    assert bundle["tasks"] == []
    assert bundle["task_count"] == 0


# ── unit-5: unknown slug / unknown change ────────────────────────────────────


async def test_get_change_bundle_unknown_slug_or_change_raises(project) -> None:
    await _seed_full_change(project)
    with pytest.raises(ResourceNotFoundError):
        await _svc().get_change_bundle("no-such-slug", "chg-a")
    with pytest.raises(ResourceNotFoundError):
        await _svc().get_change_bundle(project.slug, "does-not-exist")
