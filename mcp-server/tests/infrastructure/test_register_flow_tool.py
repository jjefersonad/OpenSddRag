"""Tests for the `register_flow` MCP tool (task-client-4 / flow-registry REQ-002).

The tool is a thin wrapper over `core.domain.flow_registry.register_flow`:
validates the manifest, then idempotently upserts the flow + its kinds.

Real isolated test database.
"""

from __future__ import annotations

import pytest

from opensddrag.db.connection import get_conn, run_migrations
from opensddrag.infrastructure.pg.tool_executors import register_flow


_DOCS_MANIFEST = {
    "flow": "register-flow-tool-docs",
    "kinds": [{"kind": "doc", "required_headings": ["## Objective"]}],
    "harness_triggers": ["on_doc_publish"],
    "skills": [],
    "commands": [],
    "claude_md_section": "## x",
}


@pytest.mark.asyncio
async def test_register_flow_tool_upserts_and_is_idempotent() -> None:
    await run_migrations()

    first = await register_flow(
        {"manifest": _DOCS_MANIFEST}, project_id=None, caller_id="t", conn=None
    )
    assert first["flow"] == _DOCS_MANIFEST["flow"]
    assert first["status"] in ("registered", "replaced")

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT kind FROM artifact_kinds WHERE flow = %s",
                (_DOCS_MANIFEST["flow"],),
            )
            assert [r[0] for r in await cur.fetchall()] == ["doc"]

    second = await register_flow(
        {"manifest": _DOCS_MANIFEST}, project_id=None, caller_id="t", conn=None
    )
    assert second["status"] == "unchanged"

    # cleanup
    async with get_conn() as conn:
        await conn.execute("DELETE FROM flows WHERE flow = %s", (_DOCS_MANIFEST["flow"],))


@pytest.mark.asyncio
async def test_register_flow_tool_rejects_malformed_manifest() -> None:
    with pytest.raises(Exception) as exc_info:
        await register_flow(
            {"manifest": {"flow": "bad", "claude_md_section": "x"}},
            project_id=None, caller_id="t", conn=None,
        )
    assert "kinds" in str(exc_info.value) or "missing" in str(exc_info.value).lower()