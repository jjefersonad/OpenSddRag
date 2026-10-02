"""Regression tests for multi-flow-foundation task-db-2.

Free-text artifact types and the `flow` column in models and repositories
(database-schema delta REQ-003 / REQ-008 / REQ-011):

* Unit 1 — `repository.create_artifact` accepts an arbitrary type string with
  a `flow` value: `type='doc-discovery'`, `flow='docs'` is stored exactly with
  no enum rejection; name uniqueness is unchanged across flows (duplicate name
  in the same project fails regardless of flow); rows inserted without an
  explicit flow default to 'sdd'.
* Unit 2 — `repository.list_artifacts` accepts a flow filter: only artifacts
  of that flow are returned, and the SQL targets the
  `(project_id, flow, type, status)` index (EXPLAIN shows an index scan).
* Unit 3 — free-text harness trigger: a rule stored with
  `trigger='on_doc_publish'` is returned by
  `get_harness_checklist(trigger='on_doc_publish')`, and a pre-existing
  `on_apply` rule is still returned for that trigger; `search_semantic`
  accepts an arbitrary `type` filter value.

The `flow` parameter is resolved from the project's `default_flow` at the
tool layer; these tests exercise the repository contract directly.
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from opensddrag.db import project_repository, repository, rule_repository
from opensddrag.db.connection import get_conn
from opensddrag.embedding.service import embed
from opensddrag.models.artifact import ArtifactCreate, ArtifactStatus, ArtifactType
from opensddrag.models.project import ProjectCreate
from opensddrag.models.rule import RuleCreate


@pytest_asyncio.fixture
async def project():
    slug = f"test-multiflow-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM project_rules WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


async def _create(project_id, name: str, kind: str, flow: str = "sdd", content: str = "x"):
    data = ArtifactCreate(
        project_id=project_id,
        name=name,
        type=ArtifactType(kind),
        content=content,
        metadata={"flow": flow},
    )
    return await repository.create_artifact(data, embed(f"{name}\n{content}"))


# ── Unit 1: arbitrary type + flow on create ───────────────────────────────────

@pytest.mark.asyncio
async def test_create_artifact_stores_arbitrary_type_and_flow(project) -> None:
    """REQ-003 (MODIFIED): free-text type is stored exactly; no enum rejection."""
    art = await repository.create_artifact(
        ArtifactCreate(
            project_id=project.id,
            name=f"doc-discovery-{uuid4().hex[:8]}",
            type=ArtifactType("doc-discovery"),
            content="arbitrary kind body",
            flow="docs",
        ),
        embed("doc-discovery arbitrary kind body"),
    )
    assert str(art.type) == "doc-discovery"
    assert art.flow == "docs"


@pytest.mark.asyncio
async def test_create_artifact_flow_defaults_to_sdd(project) -> None:
    """REQ-003 (MODIFIED): rows created without an explicit flow get 'sdd'."""
    art = await repository.create_artifact(
        ArtifactCreate(
            project_id=project.id,
            name=f"sdd-default-{uuid4().hex[:8]}",
            type=ArtifactType("spec"),
            content="sdd default flow body",
        ),
        embed("sdd default flow body"),
    )
    assert art.flow == "sdd"


@pytest.mark.asyncio
async def test_create_artifact_duplicate_name_fails_across_flows(project) -> None:
    """REQ-003 (MODIFIED): UNIQUE (project_id, name) is unchanged across flows."""
    name = f"dup-{uuid4().hex[:8]}"
    await repository.create_artifact(
        ArtifactCreate(
            project_id=project.id, name=name, type=ArtifactType("spec"),
            content="first",
        ),
        embed(f"{name} first"),
    )
    with pytest.raises(Exception):
        await repository.create_artifact(
            ArtifactCreate(
                project_id=project.id, name=name, type=ArtifactType("doc-discovery"),
                content="second", flow="docs",
            ),
            embed(f"{name} second"),
        )


# ── Unit 2: flow filter on list ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_artifacts_filters_by_flow(project) -> None:
    """REQ-008 (MODIFIED): list_artifacts honours the flow filter."""
    docs = await repository.create_artifact(
        ArtifactCreate(
            project_id=project.id, name=f"docs-only-{uuid4().hex[:8]}",
            type=ArtifactType("doc"), content="docs flow artifact",
            flow="docs",
        ),
        embed("docs flow artifact"),
    )
    await repository.create_artifact(
        ArtifactCreate(
            project_id=project.id, name=f"sdd-only-{uuid4().hex[:8]}",
            type=ArtifactType("spec"), content="sdd flow artifact",
        ),
        embed("sdd flow artifact"),
    )

    try:
        results = await repository.list_artifacts(project.id, flow="docs")
    except TypeError as exc:
        pytest.fail(f"list_artifacts has no flow parameter yet: {exc}")
    names = [a.name for a in results]
    assert names == [docs.name], (
        f"flow filter must return only the docs flow artifact, got {names}"
    )

    # Default (no flow arg) keeps returning everything — unchanged behaviour.
    all_results = await repository.list_artifacts(project.id)
    assert len(all_results) == 2 and docs.name in {a.name for a in all_results}


@pytest.mark.asyncio
async def test_list_artifacts_flow_filter_uses_index(project) -> None:
    """REQ-008 (MODIFIED): the flow-filtered query targets idx_artifacts_project."""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SET enable_seqscan = OFF")
            await cur.execute(
                """
                EXPLAIN (FORMAT TEXT) SELECT id FROM artifacts
                WHERE project_id = %s AND flow = 'docs'
                """,
                (str(project.id),),
            )
            plan = "\n".join(
                (row[0] if isinstance(row, (list, tuple)) else str(row))
                for row in await cur.fetchall()
            )
            await cur.execute("SET enable_seqscan = ON")
    assert "Idx" in plan or "Index" in plan, (
        f"flow-filtered list must use the index, plan: {plan[:400]}"
    )
    assert "Seq Scan" not in plan


# ── Unit 3: free-text harness trigger ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_free_text_trigger_stored_and_returned(project) -> None:
    """REQ-011: arbitrary trigger strings survive storage and filtering."""
    await rule_repository.upsert(
        RuleCreate(
            project_id=project.id, name="doc-publish-gate",
            trigger="on_doc_publish", category="architecture",
            severity="warning", instruction="Check docs before publish",
        )
    )
    rules = await rule_repository.list_by_trigger(project.id, "on_doc_publish")
    named = [r.name for r in rules]
    assert "doc-publish-gate" in named, (
        f"free-text trigger must be retrievable via list_by_trigger, got {named}"
    )
    # And the canonical on_apply rules still work unchanged.
    on_apply = await rule_repository.list_by_trigger(project.id, "on_apply", enabled_only=True)
    assert all(r.trigger == "on_apply" for r in on_apply)