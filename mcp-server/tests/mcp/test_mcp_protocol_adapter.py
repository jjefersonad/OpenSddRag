"""Integration test: MCPServerAdapter end-to-end via the stdio transport.

Spawns `opensddrag-server server start` as a child process, sends
JSON-RPC 2.0 messages on stdin (newline-delimited JSON, the MCP SDK's
wire format), and reads responses from stdout. This is the end-to-end
regression guard for the refactored adapter — it proves that a real
MCP client (Claude Code, the Node.js client, etc.) can still talk to
the server after the clean-architecture migration.

Requires the Docker Compose database to be up. Skipped automatically
when the database is unreachable (e.g. in CI without services).

Run directly with:
    pytest tests/mcp/test_mcp_protocol_adapter.py -v
"""

from __future__ import annotations

import json
import os
import pathlib
import select
import subprocess
import sys
import time
from typing import Any

import pytest

# ── Constants ─────────────────────────────────────────────────────────────────

_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://opensddrag:opensddrag@localhost:54326/opensddrag",
)

_SERVER_CMD: list[str] = [
    str(pathlib.Path(sys.executable).parent / "opensddrag-server"),
    "server",
    "start",
]

_STARTUP_TIMEOUT = 25.0  # seconds — accounts for migrations + model load
_REQUEST_TIMEOUT = 10.0  # seconds — per message after server is warm

_PROTO_VERSION = "2024-11-05"

# ── DB reachability guard ─────────────────────────────────────────────────────


def _db_reachable() -> bool:
    try:
        import psycopg  # type: ignore[import]

        with psycopg.connect(_DB_URL, connect_timeout=3):
            return True
    except Exception:
        return False


# ── Low-level subprocess helpers ──────────────────────────────────────────────


def _send(proc: subprocess.Popen, msg: dict[str, Any]) -> None:
    """Write one JSON-RPC message to the server's stdin."""
    line = json.dumps(msg, ensure_ascii=False) + "\n"
    assert proc.stdin is not None
    proc.stdin.write(line.encode())
    proc.stdin.flush()


def _recv(proc: subprocess.Popen, timeout: float = _STARTUP_TIMEOUT) -> dict[str, Any]:
    """Read the next JSON-RPC response from the server's stdout.

    Skips non-JSON lines (debug output) and retries until timeout.
    """
    assert proc.stdout is not None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        ready, _, _ = select.select([proc.stdout], [], [], min(remaining, 0.2))
        if not ready:
            if proc.poll() is not None:
                stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
                raise RuntimeError(
                    f"server exited with code {proc.returncode} before responding.\n"
                    f"stderr:\n{stderr}"
                )
            continue
        line = proc.stdout.readline()
        if not line:
            stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
            raise RuntimeError(
                f"server stdout closed unexpectedly.\nstderr:\n{stderr}"
            )
        text = line.decode(errors="replace").strip()
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue  # log or debug line — skip

    raise TimeoutError(
        f"no JSON-RPC response from server within {timeout}s"
    )


def _call(
    proc: subprocess.Popen,
    id_: int,
    method: str,
    params: dict[str, Any] | None = None,
    timeout: float = _REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Send a JSON-RPC request and return the matching response."""
    msg: dict[str, Any] = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        msg["params"] = params
    _send(proc, msg)
    return _recv(proc, timeout=timeout)


# ── Module-scoped server fixture ──────────────────────────────────────────────


@pytest.fixture(scope="module")
def mcp_server():
    """Spawn the MCP server, perform the handshake, yield the process.

    Skips the whole module when the DB is not reachable. Uses
    module scope so the heavyweight startup (migrations, seed,
    embedding model load) runs only once for all tests below.
    """
    if not _db_reachable():
        pytest.skip("database not reachable — start docker compose up -d to enable")

    env = os.environ.copy()
    env.setdefault("DATABASE_URL", _DB_URL)

    proc = subprocess.Popen(
        _SERVER_CMD,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    try:
        # ── MCP handshake ────────────────────────────────────────────
        # The first _recv uses _STARTUP_TIMEOUT to absorb the DB migration
        # and embedding-model warm-up that happen inside _bootstrap().
        init_resp = _call(
            proc,
            id_=1,
            method="initialize",
            params={
                "protocolVersion": _PROTO_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "pytest-adapter-test", "version": "0.0.1"},
            },
            timeout=_STARTUP_TIMEOUT,
        )
        assert init_resp.get("id") == 1, f"unexpected init response: {init_resp}"
        assert "result" in init_resp, f"init error: {init_resp}"

        # Notifications have no ID and generate no response.
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        yield proc, init_resp

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_initialize_returns_server_info(mcp_server):
    """The `initialize` response must include `serverInfo.name`."""
    _proc, init_resp = mcp_server
    result = init_resp["result"]
    assert "serverInfo" in result, f"missing serverInfo in: {result}"
    assert result["serverInfo"]["name"] == "opensddrag"


@pytest.mark.integration
def test_tools_list_returns_all_tools(mcp_server):
    """tools/list must return exactly 22 tools (alphabetically matches snapshot)."""
    proc, _init = mcp_server
    resp = _call(proc, id_=2, method="tools/list", params={})
    assert "result" in resp, f"tools/list error: {resp}"
    tools = resp["result"]["tools"]
    names = sorted(t["name"] for t in tools)

    snapshot_path = (
        pathlib.Path(__file__).parent.parent / "core" / "snapshots" / "tools_list.json"
    )
    expected_names = sorted(t["name"] for t in json.loads(snapshot_path.read_text()))

    assert names == expected_names, (
        f"Tool names differ from snapshot.\n"
        f"Got:      {names}\n"
        f"Expected: {expected_names}"
    )


@pytest.mark.integration
def test_tools_call_list_projects_returns_json(mcp_server):
    """tools/call list_projects must return valid JSON content."""
    proc, _init = mcp_server
    resp = _call(
        proc,
        id_=3,
        method="tools/call",
        params={"name": "list_projects", "arguments": {}},
    )
    assert "result" in resp, f"list_projects error: {resp}"
    content = resp["result"]["content"]
    assert isinstance(content, list) and len(content) > 0
    # The text must be valid JSON (a list of project objects).
    parsed = json.loads(content[0]["text"])
    assert isinstance(parsed, list)


@pytest.mark.integration
def test_tools_call_unknown_name_returns_tool_not_found_error(mcp_server):
    """tools/call with an unknown name returns a TOOL_NOT_FOUND error envelope."""
    proc, _init = mcp_server
    resp = _call(
        proc,
        id_=4,
        method="tools/call",
        params={"name": "nonexistent_tool_xyz", "arguments": {}},
    )
    assert "result" in resp, f"unexpected error response: {resp}"
    content = resp["result"]["content"]
    text = content[0]["text"]
    parsed = json.loads(text)
    assert parsed.get("error", {}).get("code") == "TOOL_NOT_FOUND", (
        f"expected TOOL_NOT_FOUND error, got: {text!r}"
    )
