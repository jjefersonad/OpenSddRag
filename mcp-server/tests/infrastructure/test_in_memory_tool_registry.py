"""Unit tests for `InMemoryToolRegistry`.

Spec refs:
    mcp-infrastructure-spec REQ-002 (the InMemoryRateLimiter
        sibling) — the in-memory registry is the test / fallback
        path for tool lookups.

These tests live under `tests/infrastructure/` because the
registry is an infrastructure adapter. They do NOT touch
PostgreSQL.
"""

from __future__ import annotations

import pytest

from opensddrag.core.domain.permission import Permission
from opensddrag.core.domain.tool import Tool
from opensddrag.core.ports.tool_registry import ToolRegistryPort
from opensddrag.infrastructure.memory.in_memory_tool_registry import InMemoryToolRegistry


def _make_tool(name: str, perm: Permission = Permission.READ_ONLY) -> Tool:
    return Tool(
        name=name,
        description=f"Tool {name}",
        required_permission=perm,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )


# ─── Test 1: get returns a tool by name ────────────────────────────────────


def test_get_returns_tool_by_name() -> None:
    """`get(name)` returns the `Tool` registered under `name`."""
    tools = [
        _make_tool("search_semantic"),
        _make_tool("create_artifact", Permission.WRITE),
    ]
    reg = InMemoryToolRegistry(tools)

    tool = reg.get("search_semantic")
    assert tool is not None
    assert tool.name == "search_semantic"
    assert tool.required_permission is Permission.READ_ONLY

    tool_write = reg.get("create_artifact")
    assert tool_write is not None
    assert tool_write.required_permission is Permission.WRITE


# ─── Test 2: get returns None for unknown names ──────────────────────────


def test_get_returns_none_for_unknown_name() -> None:
    """`get(name)` returns `None` for any name not in the registry.
    The use case translates this into `Response.error(code=
    "TOOL_NOT_FOUND")`.
    """
    reg = InMemoryToolRegistry([_make_tool("search_semantic")])
    assert reg.get("nonexistent") is None
    assert reg.get("") is None
    # Case sensitivity: "SEARCH_SEMANTIC" is a different name.
    assert reg.get("SEARCH_SEMANTIC") is None


# ─── Test 3: list returns all registered tools ────────────────────────────


def test_list_returns_all_registered_tools() -> None:
    """`list()` returns every tool registered, in the order they
    were passed to the constructor (dict insertion order).
    """
    tools = [
        _make_tool("a"),
        _make_tool("b"),
        _make_tool("c"),
    ]
    reg = InMemoryToolRegistry(tools)
    all_tools = reg.list()
    assert [t.name for t in all_tools] == ["a", "b", "c"]
    assert len(all_tools) == 3

    # And the returned list is a NEW list (not a view into the
    # registry's internal dict).
    all_tools.append("mutate me")
    assert "mutate me" not in [t.name for t in reg.list()]


# ─── Test 4 (bonus): empty registry ────────────────────────────────────────


def test_empty_registry() -> None:
    """An empty registry returns an empty list and `None` for any
    name. This is the steady state before any tool is registered.
    """
    reg = InMemoryToolRegistry([])
    assert reg.list() == []
    assert reg.get("anything") is None


# ─── Test 5 (bonus): satisfies the ToolRegistryPort Protocol ─────────────


def test_satisfies_tool_registry_port() -> None:
    """`InMemoryToolRegistry` MUST be a structural subtype of
    `ToolRegistryPort`.
    """
    reg = InMemoryToolRegistry([_make_tool("t")])
    assert isinstance(reg, ToolRegistryPort)


# ─── Test 6 (bonus): duplicate names raise at construction ───────────────


def test_duplicate_tool_names_raise_at_construction() -> None:
    """Two tools with the same `name` is a configuration error.
    `InMemoryToolRegistry` raises `ValueError` at construction
    time (fail fast) rather than silently overwriting the first.
    """
    tools = [_make_tool("dup"), _make_tool("dup")]
    with pytest.raises(ValueError) as exc_info:
        InMemoryToolRegistry(tools)
    assert "dup" in str(exc_info.value)


# ─── Test 7 (bonus): accepts any iterable (generator, list, tuple) ───────


def test_accepts_any_iterable_of_tools() -> None:
    """The constructor takes `Iterable[Tool]`, so a generator
    works as well as a list. This is useful for callers that
    generate tools dynamically.
    """
    reg = InMemoryToolRegistry(
        _make_tool(f"tool_{i}") for i in range(3)
    )
    assert len(reg.list()) == 3
    assert reg.get("tool_0") is not None
    assert reg.get("tool_2") is not None
    assert reg.get("tool_3") is None
