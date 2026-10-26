"""Integration tests: project list summary, live changes, project detail
aggregates (web-ui-prototype-fidelity backend-1).

Spec refs:
    - web-api-management REQ-011 (changes endpoint: live only, task semantics)
    - web-api-management REQ-012 (project list: change/phase/phases/task_progress)
    - project-management REQ-005/006/007 (progress phase, live change, task done)

Runs against the isolated test database per project convention.
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

FLOW = "sddsummary"
LIFECYCLE = [
    {"name": "Propose", "kinds": ["proposal"]},
    {"name": "Spec", "kinds": ["spec", "test"]},
    {"name": "Design", "kinds": ["design"]},
    {"name": "Tasks", "kinds": ["task"]},
    {"name": "Apply", "kinds": ["task"]},
    {"name": "Verify", "kinds": ["test"]},
    {"name": "Sync", "kinds": []},
    {"name": "Archive", "kinds": []},
]


def _svc() -> SqlManagementService:
    return SqlManagementService()


async def _register_flow() -> None:
    await register_flow(
        {
            "flow": FLOW,
            "kinds": [{"kind": k} for k in ("proposal", "spec", "design", "task", "test")],
            "harness_triggers": ["on_spec"],
            "lifecycle": LIFECYCLE,
            "commands": [{"name": "propose"}],
            "claude_md_section": "## OpenSddRag — summary\nx",
        }
    )


async def _mk(proj, name: str, kind: str, status: str = "draft", flow: str = FLOW, **meta):
    return await repository.create_artifact(
        ArtifactCreate(
            project_id=proj.id,
            name=name,
            type=kind,
            content=f"# {name}",
            metadata=meta,
            flow=flow,
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
    slug = f"test-summary-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(
        ProjectCreate(slug=slug, name=slug, description="d", language="Python")
    )
    yield proj
    await _drop(proj)


# ── unit-1: repository.list_artifact_stubs (REQ-012) ──────────────────────


async def test_list_artifact_stubs_one_query_no_content(project) -> None:
    other = await project_repository.create_project(
        ProjectCreate(slug=f"test-summary-b-{uuid4().hex[:8]}", name="b")
    )
    try:
        await _mk(project, "s-a-proposal", "proposal", change_name="c1")
        await _mk(other, "s-b-task", "task", "archived", change_name="c2")
        rows = await repository.list_artifact_stubs([project.id, other.id])
        assert {r["project_id"] for r in rows} == {project.id, other.id}
        assert all("content" not in r and "embedding" not in r for r in rows)
        sample = next(r for r in rows if r["project_id"] == other.id)
        assert {"type", "status", "flow", "metadata", "updated_at"} <= set(sample)
        assert sample["metadata"] == {"change_name": "c2"}
        assert await repository.list_artifact_stubs([]) == []
    finally:
        await _drop(other)


# ── unit-2: list_projects (REQ-012) ───────────────────────────────────────


async def test_list_projects_carries_stage_and_progress(project) -> None:
    for kind in ("proposal", "spec", "design"):
        await _mk(project, f"lp-chg-{kind}", kind, change_name="chg")
    for i in range(5):
        await _mk(project, f"lp-chg-task-{i}", "task", "archived" if i < 3 else "draft", change_name="chg")
    empty = await project_repository.create_project(
        ProjectCreate(slug=f"test-summary-empty-{uuid4().hex[:8]}", name="empty")
    )
    try:
        entries = {p["slug"]: p for p in await _svc().list_projects()}
        entry = entries[project.slug]
        assert entry["change"] == "chg"
        assert entry["phase"] == "Apply"
        phases = {p["name"]: p["status"] for p in entry["phases"]}
        assert phases["Apply"] == "active" and phases["Tasks"] == "done"
        assert len(entry["phases"]) == 8
        assert entry["task_progress"] == {"done": 3, "total": 5}
        for key in ("id", "name", "slug", "description", "language", "created_at", "updated_at"):
            assert key in entry
        assert entry["language"] == "Python"

        blank = entries[empty.slug]
        assert blank["change"] is None
        assert blank["phase"] is None
        assert blank["phases"] == []
        assert blank["task_progress"] == {"done": 0, "total": 0}
    finally:
        await _drop(empty)


# ── unit-3: list_changes (REQ-011) ────────────────────────────────────────


async def test_list_changes_excludes_historical_with_active_main_spec(project) -> None:
    await _mk(project, "hist-proposal", "proposal", "archived", change_name="hist")
    await _mk(project, "hist-task", "task", "archived", change_name="hist")
    await _mk(project, "hist-main-spec", "spec", "active", change_name="hist", is_delta=False)
    assert (await _svc().list_changes(project.slug))["items"] == []

    await _mk(project, "live-proposal", "proposal", "draft", change_name="live")
    for i in range(5):
        await _mk(project, f"live-task-{i}", "task", "archived" if i < 4 else "draft", change_name="live")
    changes = (await _svc().list_changes(project.slug))["items"]
    assert [c["change"] for c in changes] == ["live"]
    assert changes[0]["task_progress"] == {"done": 4, "total": 5}
    assert changes[0]["started_at"]
    phases = {p["name"]: p["status"] for p in changes[0]["phases"]}
    assert phases["Propose"] == "done" and phases["Apply"] == "active"


async def test_list_changes_unknown_slug_raises_not_found() -> None:
    with pytest.raises(ResourceNotFoundError):
        await _svc().list_changes("no-such-slug-summary")


# ── unit-4: get_project (REQ-005, REQ-007) ────────────────────────────────


async def test_get_project_aggregate_counts_live_changes_only(project) -> None:
    for i in range(20):
        await _mk(project, f"old-task-{i}", "task", "archived", change_name="old")
    await _mk(project, "old-main-spec", "spec", "active", change_name="old", is_delta=False)
    await _mk(project, "new-proposal", "proposal", "draft", change_name="new")
    for i in range(3):
        await _mk(project, f"new-task-{i}", "task", "draft", change_name="new")

    detail = await _svc().get_project(project.slug)
    assert detail["task_progress"] == {"done": 0, "total": 3}
    flows = {f["flow"]: f for f in detail["flows"]}
    assert flows[FLOW]["phase"] == "Tasks"
    assert flows[FLOW]["task_progress"] == {"done": 0, "total": 3}
    assert detail["summary"]["task"] == 23  # artifact counts keep covering everything


async def test_get_project_flow_without_lifecycle_has_no_phase(project) -> None:
    await _mk(project, "bare-proposal", "proposal", "draft", flow="sdd", change_name="x")
    detail = await _svc().get_project(project.slug)
    flows = {f["flow"]: f for f in detail["flows"]}
    assert flows["sdd"]["phase"] is None
