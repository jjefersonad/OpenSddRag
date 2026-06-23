"""Logger port.

Fire-and-forget structured logging for the use case. The use case calls
`info`/`warning`/`error` exactly once per invocation, after returning
the `Response` to the caller (so a logging failure never affects the
caller's response — see `apply-clean-architecture-to-mcp-server-design.md`
Decision: "`PgLogger` writes to stderr in JSON format, not to a DB
table").

The reference implementation is `PgLogger`
(`infrastructure/pg/pg_logger.py`) which writes one line of JSON to
`sys.stderr` per call. A future Loki/Datadog/Sentry adapter can be
swapped in by changing the composition root — the use case is
unaffected.

The use case calls the logger with an `event` name and arbitrary
`**fields`. The standard fields are:
    * `tool_name`       — the tool that was invoked
    * `caller_id`       — the opaque caller identifier
    * `duration_ms`     — wall time around the executor call
    * `result_status`   — `"ok"` or `"error"`
    * `error_code`      — only when `result_status == "error"`

Implementations MUST NOT raise. A logging failure is silently dropped
(worst case: one line of telemetry is lost; the caller's response is
unaffected).

This module is part of the **dependency-inversion seam** (core/ports/).
It MUST NOT import from any internal project module.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LoggerPort(Protocol):
    """Structured logger used by the use cases."""

    def info(self, event: str, **fields: Any) -> None:
        """Log a structured info event.

        Args:
            event: Stable event name in dot-separated form (e.g.
                `"tool.executed"`, `"tools.listed"`). The use case uses
                `tool.executed` for `ExecuteToolUseCase` and
                `tools.listed` for `ListToolsUseCase`.
            **fields: Arbitrary structured payload. Standard fields
                (see module docstring) are documented above.
        """
        ...

    def warning(self, event: str, **fields: Any) -> None:
        """Log a structured warning event (e.g. rate-limit fallback)."""
        ...

    def error(self, event: str, **fields: Any) -> None:
        """Log a structured error event (e.g. executor raised)."""
        ...


__all__ = ["LoggerPort"]
