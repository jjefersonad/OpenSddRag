"""Tests for rule_repository: upsert, list_all, list_by_trigger, and project isolation.

All tests use the real database — no mocks. Each test gets an isolated project
that is cleaned up on teardown.
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from opensddrag.db import project_repository, rule_repository
from opensddrag.db.connection import get_conn
from opensddrag.models.project import ProjectCreate
from opensddrag.models.rule import RuleCreate


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def project():
    slug = f"test-rules-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM project_rules WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


def _make_rule(project_id, **kwargs) -> RuleCreate:
    return RuleCreate(
        project_id=project_id,
        name=kwargs.get("name", "test-rule"),
        trigger=kwargs.get("trigger", "always"),
        category=kwargs.get("category", "architecture"),
        severity=kwargs.get("severity", "warning"),
        instruction=kwargs.get("instruction", "Test instruction"),
        enabled=kwargs.get("enabled", True),
    )


# ── upsert ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_creates_new_rule(project):
    rule = await rule_repository.upsert(_make_rule(project.id, name="brand-new-rule"))
    assert rule.name == "brand-new-rule"
    assert rule.project_id == project.id
    assert rule.trigger == "always"
    assert rule.enabled is True


@pytest.mark.asyncio
async def test_upsert_updates_existing_rule_no_duplicate(project):
    await rule_repository.upsert(_make_rule(project.id, name="upsert-me", instruction="v1"))
    updated = await rule_repository.upsert(_make_rule(project.id, name="upsert-me", instruction="v2"))
    assert updated.instruction == "v2"

    all_rules = await rule_repository.list_all(project.id, enabled_only=False)
    assert [r.name for r in all_rules].count("upsert-me") == 1


@pytest.mark.asyncio
async def test_soft_delete_sets_enabled_false(project):
    await rule_repository.upsert(_make_rule(project.id, name="to-soft-delete"))
    deleted = await rule_repository.upsert(_make_rule(project.id, name="to-soft-delete", enabled=False))
    assert deleted.enabled is False

    enabled_rules = await rule_repository.list_all(project.id, enabled_only=True)
    assert not any(r.name == "to-soft-delete" for r in enabled_rules)

    all_rules = await rule_repository.list_all(project.id, enabled_only=False)
    assert any(r.name == "to-soft-delete" for r in all_rules)


# ── list_by_trigger ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_by_trigger_severity_ordering(project):
    await rule_repository.upsert(_make_rule(project.id, name="warn-rule", trigger="on_apply", severity="warning"))
    await rule_repository.upsert(_make_rule(project.id, name="err-rule", trigger="on_apply", severity="error"))
    await rule_repository.upsert(_make_rule(project.id, name="info-rule", trigger="on_apply", severity="info"))

    results = await rule_repository.list_by_trigger(project.id, "on_apply")
    names = [r.name for r in results]

    assert names.index("err-rule") < names.index("warn-rule")
    assert names.index("warn-rule") < names.index("info-rule")


@pytest.mark.asyncio
async def test_list_by_trigger_excludes_other_triggers(project):
    await rule_repository.upsert(_make_rule(project.id, name="apply-rule", trigger="on_apply"))
    await rule_repository.upsert(_make_rule(project.id, name="always-rule", trigger="always"))

    results = await rule_repository.list_by_trigger(project.id, "on_apply")
    names = [r.name for r in results]
    assert "apply-rule" in names
    assert "always-rule" not in names


@pytest.mark.asyncio
async def test_list_by_trigger_excludes_disabled(project):
    await rule_repository.upsert(_make_rule(project.id, name="active-rule", trigger="on_verify"))
    await rule_repository.upsert(_make_rule(project.id, name="disabled-rule", trigger="on_verify", enabled=False))

    results = await rule_repository.list_by_trigger(project.id, "on_verify", enabled_only=True)
    names = [r.name for r in results]
    assert "active-rule" in names
    assert "disabled-rule" not in names


# ── list_all ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_all_with_trigger_filter(project):
    await rule_repository.upsert(_make_rule(project.id, name="apply-rule", trigger="on_apply"))
    await rule_repository.upsert(_make_rule(project.id, name="archive-rule", trigger="on_archive"))

    results = await rule_repository.list_all(project.id, trigger="on_apply")
    assert all(r.trigger == "on_apply" for r in results)
    names = [r.name for r in results]
    assert "apply-rule" in names
    assert "archive-rule" not in names


@pytest.mark.asyncio
async def test_list_all_with_category_filter(project):
    await rule_repository.upsert(_make_rule(project.id, name="arch-rule", category="architecture"))
    await rule_repository.upsert(_make_rule(project.id, name="naming-rule", category="naming"))

    results = await rule_repository.list_all(project.id, category="naming")
    assert all(r.category == "naming" for r in results)
    names = [r.name for r in results]
    assert "naming-rule" in names
    assert "arch-rule" not in names


# ── project isolation ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_project_isolation(project):
    other_slug = f"test-rules-other-{uuid4().hex[:8]}"
    other_proj = await project_repository.create_project(ProjectCreate(slug=other_slug, name=other_slug))
    try:
        await rule_repository.upsert(_make_rule(project.id, name="proj-a-rule"))
        await rule_repository.upsert(_make_rule(other_proj.id, name="proj-b-rule"))

        a_names = [r.name for r in await rule_repository.list_all(project.id)]
        b_names = [r.name for r in await rule_repository.list_all(other_proj.id)]

        assert "proj-a-rule" in a_names
        assert "proj-b-rule" not in a_names
        assert "proj-b-rule" in b_names
        assert "proj-a-rule" not in b_names
    finally:
        async with get_conn() as conn:
            await conn.execute("DELETE FROM project_rules WHERE project_id = %s", (str(other_proj.id),))
            await conn.execute("DELETE FROM projects WHERE id = %s", (str(other_proj.id),))
