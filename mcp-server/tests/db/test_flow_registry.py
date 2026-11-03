"""Tests for flow registry persistence (multi-flow-foundation, task-registry-2).

flow-registry REQ-002 — the `flows` / `artifact_kinds` tables are populated:

* Unit 1 — `init` on an empty database leaves `flows` with a `sdd` row and
  `artifact_kinds` with exactly the five SDD kind rows.
* Unit 2 — `register_flow` is idempotent: running it twice with the same
  manifest changes no rows and succeeds.
* Unit 3 — registering a *changed* manifest replaces that flow's
  `artifact_kinds` rows; other flows' rows are untouched.

The sdd seeding lives in migration 008 (idempotent seed rows) AND in the
`ensure_sdd_flow` helper called by `init`, so both paths converge on the
same rows. `register_flow_flow` in `core/domain/flow_registry.py` is the
domain gateway; the CLI subcommand `register-flow` is a thin wrapper.

Integration tests hit the real isolated test database per project
convention.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.core.domain.flow_manifest import FlowManifest
from opensddrag.db.flow_registry import (
    ensure_sdd_flow,
    register_flow,
    registered_kinds,
    registered_flows,
)
from opensddrag.db import project_repository
from opensddrag.db.connection import get_conn, run_migrations
from opensddrag.models.project import ProjectCreate


@pytest_asyncio.fixture
async def project():
    slug = f"test-flowreg-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM project_rules WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


_SDD_KINDS = {"proposal", "spec", "design", "task", "test"}

_DOCS_MANIFEST = {
    "flow": "docs",
    "kinds": [
        {"kind": "doc", "required_headings": ["## Objective"]},
        {"kind": "changelog"},
    ],
    "harness_triggers": ["on_doc_publish"],
    "skills": ["docs-outline", "docs-review"],
    "commands": [{"name": "draft", "folder": "docs"}],
    "claude_md_section": "## OpenSddRag — docs\nMarker.",
}


def _insert_marker_artifact(project_id, extra_sql: str = "") -> None:
    """Give the DB a project-side row so 'empty database' paths are realistic."""
    # Not needed for registry tables; kept for symmetry with other tests.


# ── Unit 1: init registers the sdd flow ───────────────────────────────────────


@pytest.mark.asyncio
async def test_init_registers_the_sdd_flow() -> None:
    """REQ-002: init seeds flows='sdd' + the five kinds (idempotent seed)."""
    await run_migrations()
    await ensure_sdd_flow()

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT flow FROM flows ORDER BY flow")
            flows = [r[0] for r in await cur.fetchall()]
            await cur.execute("SELECT kind FROM artifact_kinds WHERE flow = 'sdd' ORDER BY kind")
            kinds = {r[0] for r in await cur.fetchall()}

    assert "sdd" in flows
    assert kinds == _SDD_KINDS, f"kinds mismatch: {sorted(kinds)}"


# ── Unit 2: register-flow idempotency ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_flow_idempotent(project) -> None:
    """REQ-002: second run with the same manifest must be a quiet no-op."""
    await ensure_sdd_flow()

    first = await register_flow(_DOCS_MANIFEST)
    snapshot = await _registry_snapshot()
    assert flow_row_count(snapshot, "docs") == 1
    assert kind_row_count(snapshot, "docs") == 2

    second = await register_flow(_DOCS_MANIFEST)
    after = await _registry_snapshot()

    assert after == snapshot, (
        "re-registering an unchanged manifest must not change any row"
    )
    assert "unchanged" in second["status"]


# ── Unit 3: changed manifest replaces that flow's kinds ───────────────────────


@pytest.mark.asyncio
async def test_changed_manifest_replaces_kinds(project) -> None:
    """REQ-002: changed manifest swaps that flow's artifact_kinds; others keep."""
    await ensure_sdd_flow()
    await register_flow(_DOCS_MANIFEST)

    other = dict(_DOCS_MANIFEST)
    other["flow"] = "audit"
    other["kinds"] = [{"kind": "finding"}]
    await register_flow(other)

    changed = dict(_DOCS_MANIFEST)
    changed["kinds"] = [{"kind": "doc"}, {"kind": "changelog"}, {"kind": "tutorial"}]
    result = await register_flow(changed)
    assert "replaced" in result["status"]

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT kind FROM artifact_kinds WHERE flow = 'docs' ORDER BY kind"
            )
            docs_kinds = {r[0] for r in await cur.fetchall()}
            await cur.execute(
                "SELECT kind FROM artifact_kinds WHERE flow = 'audit' ORDER BY kind"
            )
            audit_kinds = {r[0] for r in await cur.fetchall()}
            await cur.execute(
                "SELECT kind FROM artifact_kinds WHERE flow = 'sdd' ORDER BY kind"
            )
            sdd_kinds = {r[0] for r in await cur.fetchall()}

    assert docs_kinds == {"doc", "changelog", "tutorial"}
    assert audit_kinds == {"finding"}
    assert sdd_kinds == _SDD_KINDS  # untouched


# ── REQ-001 abort: malformed manifest writes no partial rows ─────────────────


@pytest.mark.asyncio
async def test_malformed_manifest_aborts_with_no_partial_rows(project) -> None:
    from opensddrag.db.flow_registry import register_flow

    bad = {"flow": "broken", "kinds": [], "claude_md_section": "x"}
    await ensure_sdd_flow()
    before = await _registry_snapshot()
    with pytest.raises(Exception) as exc_info:
        await register_flow(bad)
    assert "kinds" in str(exc_info.value) or "missing" in str(exc_info.value).lower()
    assert await _registry_snapshot() == before


async def _registry_snapshot() -> dict:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT flow, manifest::text FROM flows ORDER BY flow")
            flows = {r[0]: r[1] for r in await cur.fetchall()}
            await cur.execute("SELECT flow, kind FROM artifact_kinds ORDER BY flow, kind")
            kinds = [(r[0], r[1]) for r in await cur.fetchall()]
    return {"flows": flows, "kinds": kinds}


def flow_row_count(snapshot: dict, flow: str) -> int:
    return 1 if flow in snapshot["flows"] else 0


def kind_row_count(snapshot: dict, flow: str) -> int:
    return sum(1 for f, _ in snapshot["kinds"] if f == flow)


def registered_flows(snapshot: dict) -> list[str]:
    return sorted(snapshot["flows"].keys())


def registered_kinds(snapshot: dict, flow: str) -> set[str]:
    return {k for f, k in snapshot["kinds"] if f == flow}

# ── Lifecycle persistence (web-ui-design-alignment, flow-registry delta REQ-007)


_LIFECYCLE_MANIFEST = {
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


async def test_register_flow_persists_lifecycle_and_replaces(project) -> None:
    """REQ-007: registering a manifest WITH lifecycle marks `replaced`,
    persists the lifecycle in the stored JSONB, and a second identical
    registration is `unchanged` (idempotency preserved)."""
    # First: register without lifecycle (baseline, as pre-existing manifests are)
    base = {k: v for k, v in _LIFECYCLE_MANIFEST.items() if k != "lifecycle"}
    await register_flow(base)

    # Upgrade: same flow + lifecycle => status replaced
    result = await register_flow(_LIFECYCLE_MANIFEST)
    assert result["status"] == "replaced"

    # Lifecycle persisted in the stored manifest
    from opensddrag.db.connection import get_conn
    import json

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT manifest::text FROM flows WHERE flow = 'docs'")
            stored = json.loads((await cur.fetchone())[0])
    assert stored["lifecycle"] == _LIFECYCLE_MANIFEST["lifecycle"]

    # Idempotency maintained
    again = await register_flow(_LIFECYCLE_MANIFEST)
    assert again["status"] == "unchanged"
