"""Integration: `validate_artifact` uses the (flow, kind) registry.

Proves the executor wires `repository.get_artifact_kind_rules` into
`validate_registered` (flow-registry REQ-003): declarative rules authored
via `register_flow` drive validation of a non-SDD kind, and the built-in
SDD validator keeps its exact message.

Real isolated test database, per project convention.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.core.domain.flow_registry import register_flow
from opensddrag.db import project_repository
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.pg.tool_executors import (
    create_artifact,
    validate_artifact,
)
from opensddrag.models.project import ProjectCreate


@pytest_asyncio.fixture
async def project():
    slug = f"test-kindval-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


_DOCS_MANIFEST = {
    "flow": "docs",
    "kinds": [{"kind": "doc", "required_headings": ["## Objective"]}],
    "harness_triggers": [],
    "skills": [],
    "commands": [],
    "claude_md_section": "## OpenSddRag — docs\nMarker.",
}


@pytest.mark.asyncio
async def test_validate_artifact_uses_declarative_rules(project) -> None:
    await register_flow(_DOCS_MANIFEST)
    await create_artifact(
        {
            "name": f"docs-missing-heading-{uuid4().hex[:6]}",
            "type": "doc",
            "content": "A docs body that is long enough but lacks the heading.",
            "flow": "docs",
        },
        project_id=project.id,
        caller_id="t",
        conn=None,
    )
    # find the created artifact name
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT name FROM artifacts WHERE project_id = %s AND flow = 'docs' ORDER BY created_at DESC LIMIT 1",
                (str(project.id),),
            )
            name = (await cur.fetchone())[0]

    result = await validate_artifact(
        {"name": name}, project_id=project.id, caller_id="t", conn=None
    )
    assert result == {
        "valid": False,
        "issues": ["Missing required heading: ## Objective"],
    }


@pytest.mark.asyncio
async def test_validate_artifact_sdd_spec_exact_message(project) -> None:
    await create_artifact(
        {
            "name": f"sdd-spec-{uuid4().hex[:6]}",
            "type": "spec",
            "content": "# cap Specification\n\n## Purpose\nA meaningful purpose.",
        },
        project_id=project.id,
        caller_id="t",
        conn=None,
    )
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT name FROM artifacts WHERE project_id = %s AND type = 'spec' ORDER BY created_at DESC LIMIT 1",
                (str(project.id),),
            )
            name = (await cur.fetchone())[0]

    result = await validate_artifact(
        {"name": name}, project_id=project.id, caller_id="t", conn=None
    )
    assert result == {
        "valid": False,
        "issues": ["Spec must have a 'Requirements' section."],
    }