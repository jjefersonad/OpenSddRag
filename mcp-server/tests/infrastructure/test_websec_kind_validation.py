"""Integration: `validate_artifact` applies the websec declarative rules.

Proves that the `websec` flow's manifest rules (registered via `register_flow`,
flow-registry REQ-003) drive validation of its kinds through the executor:

* finding-lifecycle REQ-001 — a `finding` without `severity` is rejected.
* authorization-gate REQ-002 — an `engagement` without `authorization` is rejected.
* A well-formed `finding` (all required headings + metadata) is accepted.

Real isolated test database, per project convention.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio

from opensddrag.db import project_repository
from opensddrag.db.connection import get_conn
from opensddrag.db.flow_registry import register_flow
from opensddrag.infrastructure.pg.tool_executors import (
    create_artifact,
    validate_artifact,
)
from opensddrag.models.project import ProjectCreate

# The websec manifest rules — mirrors client/src/templates/flows/websec/manifest.js.
_WEBSEC_MANIFEST = {
    "flow": "websec",
    "kinds": [
        {
            "kind": "engagement",
            "required_headings": [
                "Scope",
                "Authorization",
                "Rules of Engagement",
                "Out of Scope",
            ],
            "required_metadata_keys": ["target", "authorization", "scope"],
        },
        {
            "kind": "surface",
            "required_headings": ["Entry Points", "Trust Boundaries"],
            "required_metadata_keys": ["context_mode"],
        },
        {
            "kind": "finding",
            "required_headings": [
                "Affected Component",
                "Reproduction",
                "Impact",
                "Remediation",
            ],
            "required_metadata_keys": ["severity", "reference", "evidence"],
        },
        {"kind": "poc"},
        {"kind": "remediation"},
        {"kind": "report", "required_headings": ["Summary", "Findings by Severity"]},
    ],
    "harness_triggers": ["always", "on_apply", "on_verify"],
    "skills": [],
    "commands": [],
    "claude_md_section": "## OpenSddRag — websec\nMarker.",
}

_FINDING_CONTENT = (
    "## Affected Component\nLogin form\n"
    "## Reproduction\nSteps to reproduce\n"
    "## Impact\nSession hijack\n"
    "## Remediation\nEscape output"
)
_ENGAGEMENT_CONTENT = (
    "## Scope\napp.example.com\n"
    "## Authorization\nSigned SOW #12\n"
    "## Rules of Engagement\nNo DoS\n"
    "## Out of Scope\nThird-party CDN"
)


@pytest_asyncio.fixture
async def project():
    slug = f"test-websec-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj
    async with get_conn() as conn:
        await conn.execute("DELETE FROM artifacts WHERE project_id = %s", (str(proj.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


@pytest.mark.asyncio
async def test_websec_finding_missing_severity_rejected(project) -> None:
    await register_flow(_WEBSEC_MANIFEST)
    name = f"websec-finding-{uuid4().hex[:6]}"
    await create_artifact(
        {
            "name": name,
            "type": "finding",
            "flow": "websec",
            "content": _FINDING_CONTENT,
            "metadata": {"reference": "CWE-79", "evidence": "observed"},
        },
        project_id=project.id,
        caller_id="t",
        conn=None,
    )

    result = await validate_artifact(
        {"name": name}, project_id=project.id, caller_id="t", conn=None
    )
    assert result["valid"] is False
    assert "Missing required metadata key: severity" in result["issues"]


@pytest.mark.asyncio
async def test_websec_engagement_missing_authorization_rejected(project) -> None:
    await register_flow(_WEBSEC_MANIFEST)
    name = f"websec-engagement-{uuid4().hex[:6]}"
    await create_artifact(
        {
            "name": name,
            "type": "engagement",
            "flow": "websec",
            "content": _ENGAGEMENT_CONTENT,
            "metadata": {"target": "https://app.example.com", "scope": "web app"},
        },
        project_id=project.id,
        caller_id="t",
        conn=None,
    )

    result = await validate_artifact(
        {"name": name}, project_id=project.id, caller_id="t", conn=None
    )
    assert result["valid"] is False
    assert "Missing required metadata key: authorization" in result["issues"]


@pytest.mark.asyncio
async def test_websec_valid_finding_accepted(project) -> None:
    await register_flow(_WEBSEC_MANIFEST)
    name = f"websec-finding-ok-{uuid4().hex[:6]}"
    await create_artifact(
        {
            "name": name,
            "type": "finding",
            "flow": "websec",
            "content": _FINDING_CONTENT,
            "metadata": {
                "severity": "high",
                "reference": "CWE-79",
                "evidence": "reflected XSS in q param",
            },
        },
        project_id=project.id,
        caller_id="t",
        conn=None,
    )

    result = await validate_artifact(
        {"name": name}, project_id=project.id, caller_id="t", conn=None
    )
    assert result == {"valid": True, "issues": []}
