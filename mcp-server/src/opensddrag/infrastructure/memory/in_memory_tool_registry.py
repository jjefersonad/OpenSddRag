"""In-memory `ToolRegistryPort` — for tests and for the
`TOOL_REGISTRY=memory` configuration.

A simple `dict[str, Tool]` keyed by tool name. Construction takes
an `Iterable[Tool]` (typically the static list of MCP tools
declared in the composition root). `get(name)` is O(1) and
`list()` returns a snapshot of the values (the use case never
mutates the registry).

This module is part of the **infrastructure layer**
(`infrastructure/memory/`). It imports only from `core.domain.*`.
It MUST NOT import from `mcp/`, `db/`, `embedding/`, `cli/`,
`config/`, `models/`, or any other infrastructure sub-package.
"""

from __future__ import annotations

from typing import Iterable

from opensddrag.core.domain.tool import Tool
from opensddrag.core.ports.tool_registry import ToolRegistryPort


class InMemoryToolRegistry:
    """Process-local `ToolRegistryPort` backed by a `dict`.

    Constructor parameters:
        tools: An iterable of `Tool` instances to register. Two
               tools with the same `name` are a configuration
               error — the second one wins (the dict assignment
               is silent) but a `ValueError` is raised at
               construction time to fail fast.
    """

    def __init__(self, tools: Iterable[Tool]) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(
                    f"duplicate tool name {tool.name!r}: a tool with this "
                    f"name is already registered. Each MCP tool MUST have "
                    f"a unique name."
                )
            self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Return the `Tool` registered under `name`, or `None`."""
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        """Return a snapshot list of every registered `Tool`.

        The list is a NEW list (not a view) so the use case may
        sort and filter it without mutating the registry's
        internal storage. Order is the dict's insertion order
        (Python 3.7+ guarantees this), which matches the order
        the composition root passed to the constructor.
        """
        return list(self._tools.values())


__all__ = ["InMemoryToolRegistry"]
