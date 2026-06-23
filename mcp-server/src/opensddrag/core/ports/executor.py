"""Tool executor port.

Runs the actual work of a tool. The use case calls `execute(tool, parameters)`
**after** all upstream checks (registry lookup, authentication resolve,
rate-limit, input validation, authorization) have passed, and **before**
output validation. The executor is the only place in the pipeline that
is allowed to raise — the use case catches every exception and
translates it to `Response.error(code="INTERNAL", ...)` (see
`tool-execution-usecase-spec` REQ-001 Scenario "Executor error").

A future implementation may:
* Run the executor in a thread pool (`asyncio.to_thread`) for blocking
  I/O-bound work.
* Add a per-tool timeout via `asyncio.wait_for`.
* Capture the executor's stdout/stderr and surface it in
  `Response.details` for debugging.

The current implementation is `PgToolRegistry.tool_executors[name]`
in the composition root — a dict of `(name, callable)` built at
startup from the existing `_dispatch` cases in `mcp/server.py` (see
`task-adapter-1` for the migration).

This module is part of the **dependency-inversion seam** (core/ports/).
It MUST NOT import from any internal project module other than
`core.domain`.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from opensddrag.core.domain.tool import Tool


@runtime_checkable
class ToolExecutorPort(Protocol):
    """Runs the work of a single tool invocation."""

    async def execute(self, tool: Tool, parameters: dict[str, Any]) -> Any:
        """Execute `tool` with `parameters` and return its result.

        Coroutine: the concrete executors perform async DB I/O (the
        repository layer is built on the async psycopg pool), so the
        port is `async` and the use case `await`s it.

        The use case has already verified that:
          * `tool` is registered (`ToolRegistryPort.get(name)` succeeded).
          * `parameters` passed `InputValidatorPort.validate`.
          * The caller's `permission` passed `AuthorizationPolicyPort.check`.
          * The caller is within the rate limit.

        Args:
            tool: The `Tool` to execute. The implementation typically
                uses `tool.name` to dispatch (the 21 existing tools
                each have a unique name).
            parameters: The (already input-validated) parameters dict.
                The implementation MAY assume the schema matches
                `tool.input_schema`, but SHOULD NOT re-validate — that
                is the input validator's job.

        Returns:
            Any JSON-serializable value that satisfies
            `tool.output_schema`. The use case passes this through
            `OutputValidatorPort.validate` before returning it.

        Raises:
            Any exception. The use case catches and translates to
            `Response.error(code="INTERNAL", message=<sanitized>)`. The
            implementation SHOULD raise domain-meaningful exceptions
            (e.g. `KeyError`, `ValueError`) rather than generic
            `RuntimeError` so the use case can map them to specific
            error codes in the future.
        """
        ...


__all__ = ["ToolExecutorPort"]
