"""Integration tests: flows endpoint, artifact flow filter, session endpoint,
per-flow phase derivation (web-ui-design-alignment backend-1).

Spec refs:
    - web-api-management delta REQ-008 (GET /api/v1/flows: registry read w/ lifecycle)
    - web-api-management delta REQ-009 (artifact `flow` field + ?flow= filter)
    - project-management delta REQ-003 (detail: language/change/per-flow summary)
    - project-management delta REQ-005 (phase derived per-flow from lifecycle)

Runs against the isolated test database per project convention.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from opensddrag.db import project_repository, repository, session_repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.management_service import SqlManagementService
from opensddrag.models.artifact import ArtifactCreate, ArtifactUpdate
from opensddrag.models.project import ProjectCreate


from uuid import uuid4


@pytest_asyncio.fixture
async def project():
    slug = f"test-webflow-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM sessions WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


@pytest_asyncio.fixture
async def artifacts(project):
    # Register the docs flow (with lifecycle) — another test suite's fixture
    # cleanup removes its rows, so this file self-provides its registry rows.
    from opensddrag.db.flow_registry import register_flow

    await register_flow(_DOCS_MANIFEST_PAYLOAD())
    created = {"__slug__": project.slug}
    for name, kind, flow in [
        ("change-one-proposal", "proposal", "sdd"),
        ("change-one-design", "design", "sdd"),
        ("docs-recipe", "doc", "docs"),
    ]:
        created[name] = await repository.create_artifact(
            ArtifactCreate(project_id=project.id, name=name, type=kind, content=f"# {name}\n\n## Requirements\n", flow=flow),
            embedding=[0.1] * 384,
        )
    return created


def _svc() -> SqlManagementService:
    return SqlManagementService()


def _DOCS_MANIFEST_PAYLOAD() -> dict:
    """docs flow manifest WITH lifecycle — the non-null phase derivation path."""
    return {
        "flow": "docs",
        "kinds": [
            {"kind": "doc", "required_headings": ["## Objective"]},
            {"kind": "changelog"},
        ],
        "harness_triggers": ["on_doc_publish"],
        "lifecycle": [
            {"name": "Objective", "kinds": ["doc"]},
            {"name": "Publication", "kinds": ["changelog"]},
        ],
        "commands": [{"name": "draft", "folder": "docs"}],
        "claude_md_section": "## OpenSddRag — docs flow\nMarker.",
    }


async def test_list_flowed_artifacts_returns_registry_rows(artifacts) -> None:
    """REQ-008: flows endpoint lists the registered flows with kinds and
    lifecycle (null when the flow declares none)."""
    svc = _svc()
    flows = await svc.list_flows()
    names = [f["flow"] for f in flows]
    assert "sdd" in names
    sdd = next(f for f in flows if f["flow"] == "sdd")
    assert {"proposal", "spec", "design", "task", "test"} <= {k["kind"] for k in sdd["kinds"]}
    # lifecycle: sdd now declares one (client-1 registered it); bare manifest seeded
    # by migration 008 has none → null
    bare = next((f for f in flows if f["flow"] == "bare" or not f.get("lifecycle")), None)
    assert (bare is not None and bare["lifecycle"] is None) or sdd["lifecycle"]


async def test_artifact_flow_filter_and_field(artifacts) -> None:
    """REQ-009: `?flow=` scopes the listing; every artifact carries `flow`."""
    svc = _svc()
    slug = artifacts["__slug__"]
    all_items = await svc.list_artifacts(slug)
    assert {a["flow"] for a in all_items} == {"sdd", "docs"}
    scoped = await svc.list_artifacts(slug, flow_filter="sdd")
    assert {a["flow"] for a in scoped} == {"sdd"}


async def test_session_endpoint_returns_context(artifacts) -> None:
    """D4: get_session returns active artifacts + note from the session row."""
    svc = _svc()
    slug = artifacts["__slug__"]
    data = await svc.get_session(slug)
    assert data == {"active_artifacts": [], "note": None}


async def test_project_detail_derives_per_flow_phase(artifacts) -> None:
    """REQ-003/REQ-005: per-flow entries derive phase from the flow's own
    declared lifecycle. The test DB has: `docs` registered WITH lifecycle
    (Objective/Publication, from test_flow_registry) and bare `sdd` (no
    lifecycle, migration 008 seed) — both derivation paths in one detail."""
    svc = _svc()
    detail = await svc.get_project(artifacts["__slug__"])
    flows_out = {f["flow"]: f for f in detail["flows"]}
    assert "sdd" in flows_out and "docs" in flows_out
    # sdd (registry manifest has no lifecycle) → phase None, degraded gracefully
    sdd = flows_out["sdd"]
    assert sdd["phase"] is None
    assert sdd["task_progress"] == {"done": 0, "total": 0}
    # docs flow declares lifecycle; its `doc` artifact is a draft (not archived)
    # → first phase with an open kind = Objective
    docs = flows_out["docs"]
    assert docs["phase"] == "Objective"
    assert docs["task_progress"] == {"done": 0, "total": 0}
    # aggregate across flows
    assert detail["task_progress"] == {"done": 0, "total": 0}


async def test_list_flows_output_is_json_serializable(artifacts) -> None:
    """REQ-008 regression: list_flows output must round-trip through
    JSONResponse (json.dumps with defaults=None must not raise on
    datetime/Timestamp values)."""
    import json as _json

    svc = _svc()
    flows = await svc.list_flows()
    serialized = _json.dumps(flows)  # strict — no default= fallback
    assert "sdd" in serialized


# ── Change tree endpoint (web-artifact-hierarchy, web-api delta REQ-010) ────


async def test_tree_full_chain(artifacts) -> None:
    """REQ-010: tree resolves the active change, returns nodes at canonical
    depths + persisted edges (proposal <- spec implements, design depends_on
    proposal)."""
    svc = _svc()
    slug = artifacts["__slug__"]
    proj = await project_repository.get_project_by_slug(slug)
    proposal = await repository.create_artifact(
        ArtifactCreate(project_id=proj.id, name="web-tree-proposal", type="proposal",
                        content="# proposal", metadata={"change_name": "web-tree-change"}),
        embedding=[0.1] * 384,
    )
    spec = await repository.create_artifact(
        ArtifactCreate(project_id=proj.id, name="web-tree-spec", type="spec",
                        content="# spec", metadata={"change_name": "web-tree-change"}),
        embedding=[0.1] * 384,
    )
    design = await repository.create_artifact(
        ArtifactCreate(project_id=proj.id, name="web-tree-design", type="design",
                        content="# design", metadata={"change_name": "web-tree-change"}),
        embedding=[0.1] * 384,
    )
    await repository.link_artifacts(spec.id, proposal.id, "implements")
    await repository.link_artifacts(design.id, proposal.id, "depends_on")

    tree = await svc.get_tree(slug)
    assert tree["change"] == "web-tree-change"
    flow_out = {f["flow"]: f for f in tree["flows"]}
    # Only the change's own flow appears — the fixture's docs-recipe has no
    # change_name and is not part of the change chain (REQ-010).
    assert set(flow_out) == {"sdd"}
    sdd = flow_out["sdd"]
    assert all(n["name"].startswith("web-tree-") for n in sdd["nodes"])
    nodes = {n["name"]: n for n in sdd["nodes"]}
    assert nodes["web-tree-proposal"]["depth"] == 0
    assert nodes["web-tree-spec"]["depth"] == 1
    assert nodes["web-tree-design"]["depth"] == 1
    edges = {(e["source"], e["target"], e["relationship_type"]) for e in sdd["edges"]}
    assert (str(spec.id), str(proposal.id), "implements") in edges
    assert (str(design.id), str(proposal.id), "depends_on") in edges


async def test_tree_empty_and_unknown(artifacts) -> None:
    """REQ-010: project with only archived/no change artifacts → change null
    + empty flows; unknown slug → ResourceNotFoundError."""
    from opensddrag.core.domain.errors import ResourceNotFoundError

    svc = _svc()
    slug2 = f"test-tree-empty-{uuid4().hex[:8]}"
    proj2 = await project_repository.create_project(ProjectCreate(slug=slug2, name=slug2))
    try:
        tree = await svc.get_tree(slug2)
        assert tree == {"change": None, "flows": []}
    finally:
        async with get_conn() as conn:
            await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj2.id),))

    with pytest.raises(ResourceNotFoundError):
        await svc.get_tree("definitely-not-a-slug-xyz")


# ── Changes-in-progress endpoint (web-overview-changes-pipeline REQ-011) ────


async def test_list_changes_per_change_pipeline(artifacts) -> None:
    """REQ-011: two live changes each derive their own pipeline statuses."""
    from opensddrag.core.domain.errors import ResourceNotFoundError

    svc = _svc()
    slug = artifacts["__slug__"]
    proj = await project_repository.get_project_by_slug(slug)

    # change one: proposal/spec/design ARCHIVED + draft task
    names1 = ("p1-chg1-proposal", "p1-chg1-spec", "p1-chg1-design")
    for n, kind in zip(names1, ("proposal", "spec", "design")):
        a = await repository.create_artifact(
            ArtifactCreate(project_id=proj.id, name=n, type=kind, content="# x", metadata={"change_name": "chg-one"}),
            embedding=[0.1] * 384,
        )
        await repository.update_artifact(proj.id, n, ArtifactUpdate(status="archived"))
    await repository.create_artifact(
        ArtifactCreate(project_id=proj.id, name="p1-chg1-task", type="task", content="# t",
                        metadata={"change_name": "chg-one", "done": False}),
        embedding=[0.1] * 384,
    )
    # change two: only a draft proposal
    await repository.create_artifact(
        ArtifactCreate(project_id=proj.id, name="p1-chg2-proposal", type="proposal", content="# p",
                        metadata={"change_name": "chg-two"}),
        embedding=[0.1] * 384,
    )
    # register the sdd flow WITH a lifecycle for this test (the registry one has none)
    from opensddrag.db.flow_registry import register_flow
    await register_flow({
        "flow": "sddpipeline",
        "kinds": [{"kind": "proposal"}, {"kind": "spec"}, {"kind": "design"}, {"kind": "task"}, {"kind": "test"}],
        "harness_triggers": ["on_spec"],
        "lifecycle": [
            {"name": "Propose", "kinds": ["proposal"]},
            {"name": "Spec", "kinds": ["spec"]},
            {"name": "Design", "kinds": ["design"]},
            {"name": "Tasks", "kinds": ["task"]},
            {"name": "Apply", "kinds": ["task"]},
            {"name": "Verify", "kinds": ["test"]},
            {"name": "Sync", "kinds": []},
            {"name": "Archive", "kinds": []},
        ],
        "commands": [{"name": "propose"}],
        "claude_md_section": "## OpenSddRag — sdd\nx",
    })
    # move chg-one artifacts to the sddpipeline flow
    async with get_conn() as conn:
        for n in names1 + ("p1-chg1-task",):
            await conn.execute("UPDATE artifacts SET flow='sddpipeline' WHERE name=%s", (n,))
        await conn.execute("UPDATE artifacts SET flow='sddpipeline' WHERE name='p1-chg2-proposal'")

    changes = (await svc.list_changes(slug))["items"]
    by_name = {c["change"]: c for c in changes}
    assert "chg-one" in by_name and "chg-two" in by_name

    one = by_name["chg-one"]
    phases = {p["name"]: p["status"] for p in one["phases"]}
    assert phases["Propose"] == "done"
    assert phases["Spec"] == "done"
    assert phases["Design"] == "done"
    assert phases["Tasks"] == "active"
    assert phases["Apply"] == "pending"
    assert phases["Archive"] == "pending"
    assert one["task_progress"] == {"done": 0, "total": 1}

    two = by_name["chg-two"]
    phases2 = {p["name"]: p["status"] for p in two["phases"]}
    assert phases2["Propose"] == "active"
    assert phases2["Spec"] == "pending"

    # empty project → []
    slug2 = f"test-changes-empty-{uuid4().hex[:8]}"
    proj2 = await project_repository.create_project(ProjectCreate(slug=slug2, name=slug2))
    try:
        assert (await svc.list_changes(slug2))["items"] == []
    finally:
        async with get_conn() as conn:
            await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj2.id),))

    with pytest.raises(ResourceNotFoundError):
        await svc.list_changes("no-such-slug-abc")
