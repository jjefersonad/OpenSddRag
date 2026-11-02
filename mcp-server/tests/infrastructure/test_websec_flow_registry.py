"""Integration: the websec flow registers idempotently (flow-pack REQ-001).

Re-registering the websec manifest with an unchanged kinds list must report
`unchanged` and must not duplicate `artifact_kinds` rows.

Real isolated test database, per project convention.
"""

from __future__ import annotations

import pytest

from opensddrag.db.connection import get_conn
from opensddrag.db.flow_registry import register_flow

# Mirrors client/src/templates/flows/websec/manifest.js (kinds only matter here).
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


@pytest.mark.asyncio
async def test_websec_reregistration_is_idempotent() -> None:
    await register_flow(_WEBSEC_MANIFEST)
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM artifact_kinds WHERE flow = 'websec'")
            before = (await cur.fetchone())[0]

    second = await register_flow(_WEBSEC_MANIFEST)
    assert second["status"] == "unchanged"

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM artifact_kinds WHERE flow = 'websec'")
            after = (await cur.fetchone())[0]

    assert after == before == 6, "re-registration must not duplicate artifact_kinds rows"
