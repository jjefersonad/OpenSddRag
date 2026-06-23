"""Unit tests for `PgToolRegistry` — the static MCP tool registry.

Spec refs:
    tool-listing-usecase-spec — the registry is the source the
        `ListToolsUseCase` reads from.
    mcp-protocol-adapter-spec REQ-002 — the registry holds the same
        tool set the MCP adapter exposes on the wire.

The registry's tool metadata is static, so these tests do NOT touch
PostgreSQL — a dummy `conn_factory` and an empty `tool_executors`
mapping are enough to construct it.

Note on the count: `task-infra-pg-3` text says "21 tools", but the
canonical source `mcp/server.py:list_tools()` declares 22 (the task's
"21" is a stale off-by-one — the design doc enumerates 22 names while
labelling them "21"). We assert against the canonical name list so the
test never drifts when tools are added or removed.
"""

from __future__ import annotations

from opensddrag.core.ports.authentication import Permission
from opensddrag.core.ports.tool_registry import Tool, ToolRegistryPort
from opensddrag.infrastructure.pg.pg_tool_registry import PgToolRegistry


# The canonical set of MCP tool names, mirroring mcp/server.py:list_tools().
_EXPECTED_NAMES = frozenset(
    {
        "search_semantic",
        "read_artifact",
        "list_artifacts",
        "recall_episodes",
        "record_trace",
        "get_working_context",
        "update_working_context",
        "list_skills",
        "get_skill",
        "suggest_skill",
        "create_skill",
        "add_rule",
        "list_rules",
        "get_harness_checklist",
        "create_artifact",
        "update_artifact",
        "validate_artifact",
        "link_artifacts",
        "get_relationships",
        "list_projects",
        "create_project",
        "openspec_import",
    }
)

_EXPECTED_WRITE = frozenset(
    {
        "create_artifact",
        "update_artifact",
        "create_skill",
        "add_rule",
        "create_project",
        "openspec_import",
        "record_trace",
        "link_artifacts",
    }
)


def _make_registry() -> PgToolRegistry:
    """Construct a registry with a dummy conn factory and no executors."""
    return PgToolRegistry(conn_factory=lambda: None, tool_executors={})


# ─── Test 1: get returns a tool by name ────────────────────────────────────


def test_get_returns_tool_by_name() -> None:
    """`get(name)` returns the `Tool` for a registered name, with the
    correct `required_permission` (READ_ONLY for reads, WRITE for the
    mutating set).
    """
    reg = _make_registry()

    read_tool = reg.get("search_semantic")
    assert read_tool is not None
    assert isinstance(read_tool, Tool)
    assert read_tool.name == "search_semantic"
    assert read_tool.required_permission is Permission.READ_ONLY
    assert read_tool.input_schema["required"] == ["query"]

    write_tool = reg.get("create_artifact")
    assert write_tool is not None
    assert write_tool.required_permission is Permission.WRITE


# ─── Test 2: get returns None for unknown names ────────────────────────────


def test_get_returns_none_for_unknown_name() -> None:
    """`get(name)` returns `None` for any name not in the registry."""
    reg = _make_registry()
    assert reg.get("nonexistent") is None
    assert reg.get("") is None
    assert reg.get("SEARCH_SEMANTIC") is None  # case-sensitive


# ─── Test 3: list returns all entries, unique names, sorted ────────────────


def test_list_returns_all_entries_with_unique_names() -> None:
    """`list()` returns every canonical tool exactly once, sorted
    alphabetically by name, with the expected permission split.
    """
    reg = _make_registry()
    tools = reg.list()

    names = [t.name for t in tools]
    # Unique names.
    assert len(names) == len(set(names))
    # Exactly the canonical set (count follows the source, not a magic number).
    assert set(names) == _EXPECTED_NAMES
    assert len(tools) == len(_EXPECTED_NAMES)
    # Alphabetically sorted.
    assert names == sorted(names)

    # Permission split matches the WRITE set; everything else is READ_ONLY.
    for tool in tools:
        expected = (
            Permission.WRITE
            if tool.name in _EXPECTED_WRITE
            else Permission.READ_ONLY
        )
        assert tool.required_permission is expected, (
            f"{tool.name} should be {expected}, got {tool.required_permission}"
        )


# ─── Test 4 (bonus): satisfies the ToolRegistryPort Protocol ───────────────


def test_satisfies_tool_registry_port() -> None:
    """`PgToolRegistry` MUST be a structural subtype of `ToolRegistryPort`."""
    assert isinstance(_make_registry(), ToolRegistryPort)


# ─── Test 5 (bonus): executor_for returns the wired executor ───────────────


def test_executor_for_returns_wired_executor() -> None:
    """`executor_for(name)` returns the injected executor, or `None`
    when no executor was wired for that tool.
    """

    class _Exec:
        def execute(self, tool, parameters):  # noqa: ANN001 - test stub
            return None

    exec_obj = _Exec()
    reg = PgToolRegistry(
        conn_factory=lambda: None,
        tool_executors={"search_semantic": exec_obj},
    )
    assert reg.executor_for("search_semantic") is exec_obj
    assert reg.executor_for("create_artifact") is None
