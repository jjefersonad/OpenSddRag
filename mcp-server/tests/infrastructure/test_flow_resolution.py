"""Tests for flow resolution + cross-flow linking (task-registry-4).

flow-registry REQ-004 — `create_artifact`, `list_artifacts`,
`search_semantic`, `get_harness_checklist` accept an optional `flow`; when
omitted, it resolves from the project's `default_flow` (else `'sdd'`).

flow-registry REQ-005 — `link_artifacts` connects artifacts of different
flows; the three relationship types and idempotency are unchanged.

Integration tests against the real isolated test database.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.db import project_repository, repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.pg.tool_executors import (
    create_artifact,
    link_artifacts,
    list_artifacts,
)
from opensddrag.models.project import ProjectCreate


@pytest_asyncio.fixture
async def project():
    slug = f"test-flowres-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


async def _set_default_flow(project_id, flow: str) -> None:
    async with get_conn() as conn:
        await conn.execute(
            "UPDATE projects SET default_flow = %s WHERE id = %s",
            (flow, str(project_id)),
        )


async def _create(project_id, name, kind, flow=None, content="Content body long enough."):
    args = {"name": name, "type": kind, "content": content}
    if flow is not None:
        args["flow"] = flow
    await create_artifact(args, project_id=project_id, caller_id="t", conn=None)


async def _flow_of(project_id, name) -> str:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT flow FROM artifacts WHERE project_id = %s AND name = %s",
                (str(project_id), name),
            )
            return (await cur.fetchone())[0]


# ── Unit 1: omitted flow resolves to sdd default ─────────────────────────────


@pytest.mark.asyncio
async def test_omitted_flow_resolves_to_sdd(project) -> None:
    """REQ-004: no flow arg in a default_flow='sdd' project → flow='sdd'."""
    name = f"no-flow-{uuid4().hex[:6]}"
    await _create(project.id, name, "spec")
    assert await _flow_of(project.id, name) == "sdd"


@pytest.mark.asyncio
async def test_omitted_flow_resolves_project_default(project) -> None:
    """REQ-004: no flow arg in a default_flow='docs' project → flow='docs'."""
    await _set_default_flow(project.id, "docs")
    name = f"docs-default-{uuid4().hex[:6]}"
    await _create(project.id, name, "doc", content="A docs artifact body.")
    assert await _flow_of(project.id, name) == "docs"


# ── Unit 2: project default_flow honored by list_artifacts ────────────────────


@pytest.mark.asyncio
async def test_list_artifacts_default_flow_honored(project) -> None:
    """REQ-004: list without flow in a default_flow='docs' project → docs only."""
    await _set_default_flow(project.id, "docs")
    await _create(project.id, f"docs-a-{uuid4().hex[:6]}", "doc", flow="docs",
                  content="A docs artifact body here.")
    await _create(project.id, f"sdd-a-{uuid4().hex[:6]}", "spec", flow="sdd",
                  content="An sdd artifact body here.")

    results = await list_artifacts({}, project_id=project.id, caller_id="t", conn=None)
    listed_names = {r["name"] for r in results}

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT name FROM artifacts WHERE project_id = %s AND flow = 'docs'",
                (str(project.id),),
            )
            docs_names = {r[0] for r in await cur.fetchall()}
            await cur.execute(
                "SELECT name FROM artifacts WHERE project_id = %s AND flow = 'sdd'",
                (str(project.id),),
            )
            sdd_names = {r[0] for r in await cur.fetchall()}

    assert docs_names and sdd_names  # both flows exist at rest
    assert listed_names == docs_names, (
        f"list without flow must return only default_flow artifacts; got {listed_names}"
    )


# ── Unit 3: cross-flow linking permitted ─────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_flow_linking_permitted(project) -> None:
    """REQ-005: an audit→sdd relates_to link is created and idempotent."""
    audit = f"audit-finding-{uuid4().hex[:6]}"
    sdd = f"sdd-task-{uuid4().hex[:6]}"
    await _create(project.id, audit, "finding", flow="audit",
                  content="A finding body long enough.")
    await _create(project.id, sdd, "task", flow="sdd",
                  content="## Goal\nSomething.\n\n## Acceptance Criteria\n- [ ] x")

    first = await link_artifacts(
        {"source_name": audit, "target_name": sdd, "relationship_type": "relates_to"},
        project_id=project.id, caller_id="t", conn=None,
    )
    assert "Linked" in first, first

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM artifacts WHERE project_id = %s AND name = %s",
                (str(project.id), audit),
            )
            audit_id = (await cur.fetchone())[0]

    rels = await repository.get_relationships(audit_id)
    assert any(r["relationship_type"] == "relates_to" for r in rels), rels

    # idempotent re-link — no duplicate row
    await link_artifacts(
        {"source_name": audit, "target_name": sdd, "relationship_type": "relates_to"},
        project_id=project.id, caller_id="t", conn=None,
    )
    rels2 = await repository.get_relationships(audit_id)
    assert sum(1 for r in rels2 if r["relationship_type"] == "relates_to") == 1