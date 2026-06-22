"""Regression test: MCPServerAdapter.list_tools() matches the golden snapshot.

Verifies that the refactored adapter returns exactly the same 22 tools
(name + description + inputSchema) as the snapshot captured at the time
the adapter migration was completed. A diff means a tool was added,
removed, renamed, or had its schema changed — all of which require a
deliberate snapshot update.

The test is DB-free: it builds use cases in in-memory mode (no
`database_url`), so it runs fast and does not require the Postgres
container to be up.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from opensddrag.infrastructure.composition import build_use_cases
from opensddrag.mcp.server import MCPServerAdapter

_SNAPSHOT_PATH = pathlib.Path(__file__).parent.parent / "core" / "snapshots" / "tools_list.json"


class _InMemorySettings:
    """Minimal settings that force `build_use_cases` into in-memory mode."""

    database_url: str = ""
    rate_limiter: str = "memory"
    rate_limiter_quota: int = 60
    rate_limiter_window_seconds: int = 60


@pytest.mark.asyncio
async def test_tools_list_matches_snapshot() -> None:
    """list_tools() output sorted by name must equal the stored snapshot."""
    use_cases = build_use_cases(_InMemorySettings())
    adapter = MCPServerAdapter(use_cases)

    tools = await adapter.list_tools()

    actual = sorted(
        [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in tools
        ],
        key=lambda d: d["name"],
    )

    expected = json.loads(_SNAPSHOT_PATH.read_text())

    assert actual == expected, (
        f"Tool list diverged from snapshot at {_SNAPSHOT_PATH}.\n"
        f"Run the snapshot generator to update it if the change is intentional:\n"
        f"  .venv/bin/python -c \"import json; from opensddrag.infrastructure.pg.pg_tool_registry import PgToolRegistry; from opensddrag.db.connection import get_conn; r = PgToolRegistry(get_conn, tool_executors={{}}); tools = sorted(r.list(), key=lambda t: t.name.lower()); print(json.dumps([{{'name': t.name, 'description': t.description, 'inputSchema': t.input_schema}} for t in tools], indent=2))\" > tests/core/snapshots/tools_list.json"
    )
