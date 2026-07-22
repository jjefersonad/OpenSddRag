"""Tests for `opensddrag.cli._seeds` — global harness rule seeding.

These tests cover the contract required by the
`embed-tdd-in-sdd-workflow` change's `task-harness-1`:

* the `tdd-first` rule is seeded into every project on `init`
  (REQ-001 of `tdd-red-green-refactor`)
* the rule text mentions the `metadata.test_exempt=true` escape hatch
  (sdd-workflow-lifecycle REQ-005 MODIFIED)
* re-seeding is idempotent: no duplicate `(project_id, name)` rows

All tests use the real database — no mocks. Each test gets isolated projects
that are cleaned up on teardown.
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from opensddrag.cli import _seeds
from opensddrag.db import project_repository, rule_repository
from opensddrag.db.connection import get_conn
from opensddrag.models.project import ProjectCreate


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def projects():
    """Create a small fleet of projects and clean them up after the test."""
    slugs = [f"test-seeds-{uuid4().hex[:8]}-{i}" for i in range(3)]
    created = []
    for slug in slugs:
        proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
        created.append(proj)
    yield created
    async with get_conn() as conn:
        for proj in created:
            await conn.execute("DELETE FROM project_rules WHERE project_id = %s", (str(proj.id),))
            await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


# ── seed_global_harness_rules ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seed_creates_tdd_first_rule_for_every_project(projects):
    await _seeds.seed_global_harness_rules()

    for project in projects:
        rules = await rule_repository.list_all(project.id, enabled_only=True)
        names = [r.name for r in rules]
        assert "tdd-first" in names, f"Rule missing for project '{project.slug}'"


@pytest.mark.asyncio
async def test_seeded_rule_has_required_contract(projects):
    await _seeds.seed_global_harness_rules()

    for project in projects:
        rules = await rule_repository.list_all(project.id, enabled_only=False)
        tdd = next((r for r in rules if r.name == "tdd-first"), None)
        assert tdd is not None
        # Spec REQ-001 (tdd-red-green-refactor) contract
        assert tdd.severity == "error"
        assert tdd.trigger == "on_apply"
        assert tdd.enabled is True
        # Stack-agnostic: every supported runner is mentioned
        instr = tdd.instruction
        for runner in ("pytest", "vitest", "jest", "go test"):
            assert runner in instr, f"runner {runner!r} missing from tdd-first instruction"
        # Escape hatch references sdd-workflow-lifecycle REQ-005 (MODIFIED)
        assert "test_exempt" in instr
        assert "REQ-005" in instr
        # Metadata traces the rule back to its origin change + capability
        assert tdd.metadata.get("origin_change") == "embed-tdd-in-sdd-workflow"
        assert tdd.metadata.get("capability") == "tdd-red-green-refactor"


@pytest.mark.asyncio
async def test_seed_is_idempotent_no_duplicate_rows(projects):
    # First seed
    await _seeds.seed_global_harness_rules()
    # Re-seed (simulate re-running `init`)
    await _seeds.seed_global_harness_rules()
    await _seeds.seed_global_harness_rules()

    for project in projects:
        all_rules = await rule_repository.list_all(project.id, enabled_only=False)
        names = [r.name for r in all_rules]
        assert names.count("tdd-first") == 1, (
            f"Expected exactly one 'tdd-first' rule for project "
            f"'{project.slug}', found {names.count('tdd-first')}"
        )


@pytest.mark.asyncio
async def test_seed_upsert_replaces_existing_rule_without_duplicating(projects):
    project = projects[0]
    # Pre-install a user-customised variant of the rule (different instruction)
    custom_override = {
        **_seeds._TDD_FIRST_RULE_TEMPLATE,
        "instruction": "user-customised: do something else entirely",
    }
    from opensddrag.models.rule import RuleCreate

    await rule_repository.upsert(
        RuleCreate(project_id=project.id, **custom_override)
    )

    await _seeds.seed_global_harness_rules()

    all_rules = await rule_repository.list_all(project.id, enabled_only=False)
    tdd_rules = [r for r in all_rules if r.name == "tdd-first"]
    assert len(tdd_rules) == 1
    # Seed function wins on re-seed (upsert replaces) — the rule content is
    # the canonical one from `_TDD_FIRST_RULE_TEMPLATE`
    assert "RED → GREEN → REFACTOR" in tdd_rules[0].instruction
