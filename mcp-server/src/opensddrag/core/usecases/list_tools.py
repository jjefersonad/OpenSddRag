"""ListToolsUseCase — the MCP `tools/list` orchestrator.

Returns the list of tools visible to a given caller profile, already
filtered by the authorization policy and ordered deterministically.
The use case is **synchronous** (no I/O) and depends only on the
read-only ports of the registry, the policy, and the logger.

This is the only use case that calls the `AuthorizationPolicyPort` for
*listing* purposes (the `ExecuteToolUseCase` calls it per-invocation,
not per-tool). The same `AuthorizationPolicyPort` implementation is
shared, so a tool that is denied to a caller for `list_for` is also
denied to that caller in `execute`.

This module is part of the **use-case layer** (core/usecases/). It MUST
NOT import from any internal project module other than `core.domain`
and `core.ports`. The architecture test in
`tests/architecture/test_imports.py::test_usecases_have_no_infra_or_db_imports`
enforces this.
"""

from __future__ import annotations

from opensddrag.core.domain.permission import (
    Allow,
    Deny,
    Permission,
    RequireConfirmation,
)
from opensddrag.core.domain.tool import Tool
from opensddrag.core.ports.authorization import AuthorizationPolicyPort
from opensddrag.core.ports.logger import LoggerPort
from opensddrag.core.ports.tool_registry import ToolRegistryPort


# Canonical event name for the log line. Module-level constant so a
# typo in the test is a NameError, not a silent mismatch.
EVENT_TOOLS_LISTED = "tools.listed"


class ListToolsUseCase:
    """Lists the tools visible to a given caller profile.

    The use case is **stateless** and **side-effect free** apart from
    the structured log line it emits (which the logger may decide to
    drop). Tests can exercise every branch with `unittest.mock.Mock`
    instances and zero I/O fixtures (see
    `tests/core/test_list_tools_usecase.py`).
    """

    def __init__(
        self,
        *,
        tool_registry: ToolRegistryPort,
        authorization_policy: AuthorizationPolicyPort,
        logger: LoggerPort,
    ) -> None:
        # Keyword-only — a future addition of a 4th port (e.g. a
        # "tenant resolver" for multi-tenant scoping) won't break
        # existing call sites in tests.
        self._tool_registry = tool_registry
        self._authorization_policy = authorization_policy
        self._logger = logger

    def list_for(self, caller_permission: Permission) -> list[Tool]:
        """Return the tools visible to a caller with `caller_permission`.

        Algorithm:
            1. Snapshot the registry (so we can sort + filter without
               mutating the registry's internal state — the spec
               requires the function to "return a NEW list").
            2. Filter by `AuthorizationPolicyPort.check` — a tool is
               included iff the policy returns `Allow()`. `Deny` and
               `RequireConfirmation` are excluded: the caller cannot
               invoke the tool without a confirmation step (for
               `RequireConfirmation`) or cannot invoke it at all (for
               `Deny`). Hiding both from the listing is the safer
               default: clients should not see tools they cannot
               immediately use.
            3. Sort the remaining tools by `Tool.name` (case-insensitive
               ascending) — the MCP `tools/list` response must be
               deterministic across calls.
            4. Emit a structured log line via the injected
               `LoggerPort.info` with the event name `"tools.listed"`,
               the `caller_permission` and the resulting `count`.

        Args:
            caller_permission: The `Permission` resolved by the
                `AuthenticationPort` for the current caller. In the
                MCP adapter this is `caller.permission` from the
                `Caller` built by `_resolve_caller`. The use case
                receives the bare `Permission` (not a `Caller`) because
                it has no use for `caller_id` — listing is not
                rate-limited (a future change may add a per-caller
                rate limit on `list_for`, in which case this signature
                would change to take a `Caller`).

        Returns:
            A **new** list of `Tool`, sorted, filtered, never `None`.
            Returns `[]` (not `None`, not a sentinel) when nothing is
            visible — a property `list_for` is free to satisfy because
            it does no I/O.
        """
        # ── Step 1: snapshot the registry ───────────────────────────
        # The port's `list()` returns an `Iterable[Tool]`. We
        # materialise it into a list because we need to iterate it
        # twice (once for filtering, once for sorting) and the spec
        # mandates we return a NEW list — so the registry's own
        # internal list (if any) is never exposed and never mutated.
        all_tools = list(self._tool_registry.list())

        # ── Step 2: filter by authorization policy ──────────────────
        # `isinstance(decision, Allow)` is the single source of truth
        # for "the caller may invoke this tool". `Deny` and
        # `RequireConfirmation` are both excluded (see docstring):
        # the spec wording is "filters out any tool where ... returns
        # `Deny`", and we extend that to `RequireConfirmation` for
        # safety — a tool requiring confirmation is not yet authorized.
        allowed: list[Tool] = []
        for tool in all_tools:
            decision = self._authorization_policy.check(caller_permission, tool)
            if isinstance(decision, Allow):
                allowed.append(tool)
            # Deny and RequireConfirmation are both dropped. We do not
            # raise — the use case is total.

        # ── Step 3: sort deterministically ───────────────────────────
        # `sorted(..., key=lambda t: t.name.lower())` gives
        # case-insensitive ascending order. We do NOT mutate the
        # registry's list (`all_tools`) — `sorted` returns a new list.
        sorted_tools = sorted(allowed, key=lambda t: t.name.lower())

        # ── Step 4: structured log ───────────────────────────────────
        self._logger.info(
            EVENT_TOOLS_LISTED,
            caller_permission=caller_permission.value,
            count=len(sorted_tools),
        )

        return sorted_tools


__all__ = [
    "EVENT_TOOLS_LISTED",
    "ListToolsUseCase",
]
