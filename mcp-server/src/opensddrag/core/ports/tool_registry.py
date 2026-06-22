"""Tool registry port.

The use case's source of truth for *which* tools exist and *how* they
look. Implementations range from a static in-memory list (the
`InMemoryToolRegistry` for tests) to a Postgres-backed registry that
hydrates from a `tools` table (the future `PgToolRegistry`).

The use case calls `get(name)` exactly once per invocation, and `list()`
zero or more times (the `ListToolsUseCase` calls `list()`; the
`ExecuteToolUseCase` does not). The port is **read-only** from the use
case's perspective — registration is done at startup by the composition
root, not at runtime.

This module is part of the **dependency-inversion seam** (core/ports/).
It MUST NOT import from any internal project module other than
`core.domain`.
"""

from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable

from opensddrag.core.domain.tool import Tool


@runtime_checkable
class ToolRegistryPort(Protocol):
    """Read-only registry of `Tool` instances."""

    def get(self, name: str) -> Tool | None:
        """Return the `Tool` registered under `name`, or `None` if absent.

        Implementations MUST be O(1) (a dict lookup) — `get` is on the hot
        path of every `ExecuteToolUseCase.execute()` call.

        Args:
            name: The stable tool name as exposed on the MCP wire
                (e.g. `"search_semantic"`). Case-sensitive.

        Returns:
            The matching `Tool`, or `None` if no tool is registered under
            `name`. The use case translates `None` into
            `Response.error(code="TOOL_NOT_FOUND", ...)` — the port MUST
            NOT raise `KeyError`.
        """
        ...

    def list(self) -> Iterable[Tool]:
        """Return an iterable of every registered `Tool`.

        Order is **not** part of the contract — callers that need a
        specific order (e.g. `ListToolsUseCase`, which sorts
        alphabetically) MUST sort the result themselves. This keeps the
        port's implementation trivial (a `dict.values()` is enough).

        Returns:
            An iterable of `Tool`. May be a list, tuple, generator, or
            any other `Iterable[Tool]`. The contract is single-pass:
            callers may iterate it once.
        """
        ...


__all__ = ["ToolRegistryPort"]
