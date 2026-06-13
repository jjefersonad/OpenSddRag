"""End-to-end tests for the harness MCP tools and the modified get_working_context.

Calls the server's `call_tool` handler directly against the real database.
Each test uses an isolated project cleaned up on teardown.
"""

import json

import pytest
import pytest_asyncio
from uuid import uuid4

from opensddrag.db import project_repository, rule_repository
from opensddrag.db.connection import get_conn
from opensddrag.models.project import ProjectCreate
from opensddrag.models.rule import RuleCreate
from opensddrag.mcp.server import call_tool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse(result) -> object:
    """Parse the JSON text from the first TextContent in a call_tool result."""
    return json.loads(result[0].text)


def _text(result) -> str:
    return result[0].text


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def project():
    slug = f"test-mcp-harness-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM project_rules WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM sessions WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


def _rule_args(slug, **kwargs) -> dict:
    return {
        "name": kwargs.get("name", "test-rule"),
        "trigger": kwargs.get("trigger", "always"),
        "category": kwargs.get("category", "architecture"),
        "severity": kwargs.get("severity", "warning"),
        "instruction": kwargs.get("instruction", "Test instruction"),
        "project_slug": slug,
        **{k: v for k, v in kwargs.items() if k not in ("name", "trigger", "category", "severity", "instruction")},
    }


# ── add_rule ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_rule_creates_rule_in_db(project):
    result = await call_tool("add_rule", _rule_args(
        project.slug,
        name="new-arch-rule",
        trigger="always",
        category="architecture",
        severity="error",
        instruction="Never write queries in route handlers.",
    ))
    data = _parse(result)
    assert data["name"] == "new-arch-rule"
    assert data["trigger"] == "always"
    assert data["severity"] == "error"
    assert data["enabled"] is True

    db_rules = await rule_repository.list_all(project.id)
    assert any(r.name == "new-arch-rule" for r in db_rules)


@pytest.mark.asyncio
async def test_add_rule_invalid_trigger_returns_error(project):
    result = await call_tool("add_rule", _rule_args(
        project.slug,
        name="bad-trigger-rule",
        trigger="on_deploy",
        category="architecture",
        instruction="Some instruction.",
    ))
    assert "Error" in _text(result)
    assert "trigger" in _text(result).lower()


@pytest.mark.asyncio
async def test_add_rule_soft_delete_via_enabled_false(project):
    await call_tool("add_rule", _rule_args(project.slug, name="disable-me", trigger="always", category="forbidden", instruction="x"))
    result = await call_tool("add_rule", {
        "name": "disable-me",
        "trigger": "always",
        "category": "forbidden",
        "instruction": "x",
        "enabled": False,
        "project_slug": project.slug,
    })
    data = _parse(result)
    assert data["enabled"] is False


# ── list_rules ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_rules_returns_correct_shape(project):
    await call_tool("add_rule", _rule_args(project.slug, name="shape-rule", trigger="on_apply", category="doc-sync", instruction="Update CHANGELOG."))
    result = await call_tool("list_rules", {"project_slug": project.slug})
    data = _parse(result)
    assert isinstance(data, list)
    assert len(data) >= 1
    rule = next(r for r in data if r["name"] == "shape-rule")
    assert rule["trigger"] == "on_apply"
    assert rule["category"] == "doc-sync"
    assert rule["enabled"] is True
    assert "id" in rule
    assert "instruction" in rule


@pytest.mark.asyncio
async def test_list_rules_excludes_disabled_by_default(project):
    await call_tool("add_rule", _rule_args(project.slug, name="active-rule", trigger="always", category="naming", instruction="Use kebab-case."))
    await call_tool("add_rule", {
        "name": "disabled-rule",
        "trigger": "always",
        "category": "naming",
        "instruction": "Disabled.",
        "enabled": False,
        "project_slug": project.slug,
    })
    result = await call_tool("list_rules", {"project_slug": project.slug})
    names = [r["name"] for r in _parse(result)]
    assert "active-rule" in names
    assert "disabled-rule" not in names


# ── get_harness_checklist ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_harness_checklist_empty_when_no_rules(project):
    result = await call_tool("get_harness_checklist", {"trigger": "on_apply", "project_slug": project.slug})
    data = _parse(result)
    assert data == []


@pytest.mark.asyncio
async def test_get_harness_checklist_returns_rules_sorted_error_first(project):
    await rule_repository.upsert(RuleCreate(
        project_id=project.id, name="warn-apply", trigger="on_apply",
        category="verification", severity="warning", instruction="SHOULD run tests.",
    ))
    await rule_repository.upsert(RuleCreate(
        project_id=project.id, name="err-apply", trigger="on_apply",
        category="verification", severity="error", instruction="MUST run tests.",
    ))

    result = await call_tool("get_harness_checklist", {"trigger": "on_apply", "project_slug": project.slug})
    data = _parse(result)
    names = [r["name"] for r in data]
    assert names.index("err-apply") < names.index("warn-apply")
    for rule in data:
        assert set(rule.keys()) >= {"name", "category", "severity", "instruction"}


@pytest.mark.asyncio
async def test_get_harness_checklist_invalid_trigger_returns_error(project):
    result = await call_tool("get_harness_checklist", {"trigger": "always", "project_slug": project.slug})
    assert "Error" in _text(result)
    assert "trigger" in _text(result).lower()


@pytest.mark.asyncio
async def test_get_harness_checklist_excludes_disabled_rules(project):
    await rule_repository.upsert(RuleCreate(
        project_id=project.id, name="disabled-check", trigger="on_verify",
        category="verification", severity="error", instruction="Must verify.", enabled=False,
    ))
    result = await call_tool("get_harness_checklist", {"trigger": "on_verify", "project_slug": project.slug})
    data = _parse(result)
    assert not any(r["name"] == "disabled-check" for r in data)


# ── get_working_context (harness injection) ───────────────────────────────────

@pytest.mark.asyncio
async def test_get_working_context_includes_rules_key(project):
    result = await call_tool("get_working_context", {"project_slug": project.slug})
    data = _parse(result)
    assert "rules" in data
    assert isinstance(data["rules"], list)


@pytest.mark.asyncio
async def test_get_working_context_rules_empty_when_no_always_rules(project):
    result = await call_tool("get_working_context", {"project_slug": project.slug})
    data = _parse(result)
    assert data["rules"] == []


@pytest.mark.asyncio
async def test_get_working_context_injects_always_rules(project):
    await rule_repository.upsert(RuleCreate(
        project_id=project.id, name="always-arch", trigger="always",
        category="architecture", severity="error", instruction="Use the repository pattern.",
    ))
    result = await call_tool("get_working_context", {"project_slug": project.slug})
    data = _parse(result)
    names = [r["name"] for r in data["rules"]]
    assert "always-arch" in names


@pytest.mark.asyncio
async def test_get_working_context_excludes_non_always_triggers(project):
    await rule_repository.upsert(RuleCreate(
        project_id=project.id, name="apply-rule-ctx", trigger="on_apply",
        category="doc-sync", severity="warning", instruction="Update CHANGELOG.",
    ))
    result = await call_tool("get_working_context", {"project_slug": project.slug})
    data = _parse(result)
    names = [r["name"] for r in data["rules"]]
    assert "apply-rule-ctx" not in names


@pytest.mark.asyncio
async def test_get_working_context_excludes_disabled_always_rules(project):
    await rule_repository.upsert(RuleCreate(
        project_id=project.id, name="disabled-always", trigger="always",
        category="forbidden", severity="error", instruction="Disabled rule.", enabled=False,
    ))
    result = await call_tool("get_working_context", {"project_slug": project.slug})
    data = _parse(result)
    names = [r["name"] for r in data["rules"]]
    assert "disabled-always" not in names


@pytest.mark.asyncio
async def test_get_working_context_preserves_existing_fields(project):
    result = await call_tool("get_working_context", {"project_slug": project.slug})
    data = _parse(result)
    assert "id" in data
    assert "project_id" in data
    assert "active_artifact_ids" in data
    assert "context" in data
