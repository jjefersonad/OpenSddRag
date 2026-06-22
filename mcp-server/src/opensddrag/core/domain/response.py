"""Domain `Response` value object.

`Response` is the **total return type** of `ExecuteToolUseCase.execute()`:
every code path — success, unknown tool, validation failure, authorization
denial, rate limit, executor error — returns a `Response` (success or
error), never raises. This is the contract that makes the use case
trivially testable (no exception types to mock) and that lets the MCP
adapter serialize a uniform `CallToolResult` (mcp-protocol-adapter-spec
REQ-001 Scenario "`tools/call` returns domain `Response`").

This module is part of the **pure domain layer** (core/domain/). It MUST
NOT import from `mcp`, `fastmcp`, `starlette`, `psycopg`, `pydantic_settings`,
`sentence_transformers`, or any internal project module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Response:
    """The result of a tool invocation, as seen by the use case.

    Constructed via the two classmethods `Response.ok(...)` and
    `Response.error(...)`. Direct construction is allowed but discouraged
    outside the use case itself — the classmethods are the public API.

    Fields:
        is_ok:   True for successful calls, False for errors. Also the
                 `kind` discriminator used by the MCP adapter to choose
                 between `CallToolResult(isError=False)` and
                 `CallToolResult(isError=True)`.
        value:   The successful return value (only meaningful when
                 `is_ok=True`). Whatever the executor returned after
                 output validation passed.
        code:    Stable machine-readable error code (only meaningful when
                 `is_ok=False`). Examples: "TOOL_NOT_FOUND", "INVALID_INPUT",
                 "FORBIDDEN", "RATE_LIMITED", "INTERNAL", "INVALID_OUTPUT".
                 The MCP adapter passes this through unchanged.
        message: Human-readable error message (only meaningful when
                 `is_ok=False`). Surfaced to the operator; safe to log.
        details: Optional structured payload for errors that carry extra
                 context — e.g. `{"errors": [{"path": "query", "message":
                 "field required"}]}` for `INVALID_INPUT`, or
                 `{"retry_after": 12}` for `RATE_LIMITED`. The MCP adapter
                 serializes this into the `text` content of the
                 `CallToolResult` as a JSON object alongside `code`/`message`.

    The combination `(code, is_ok, message)` is part of the public
    contract: changing any of these values is a breaking change for MCP
    clients (per mcp-protocol-adapter-spec REQ-001 "Public tool names are
    preserved", extended by analogy to error envelopes).
    """

    is_ok: bool
    value: Any = None
    code: str | None = None
    message: str | None = None
    details: Any = field(default=None)

    @classmethod
    def ok(cls, value: Any) -> Response:
        """Build a successful response.

        Example:
            Response.ok({"name": "search_semantic", "results": [...]})
        """
        return cls(is_ok=True, value=value)

    @classmethod
    def error(
        cls,
        code: str,
        message: str,
        *,
        details: Any = None,
    ) -> Response:
        """Build an error response with a stable code and human message.

        Args:
            code:    Stable machine-readable identifier. Convention is
                     SCREAMING_SNAKE_CASE.
            message: Human-readable explanation. Safe to log. MUST NOT
                     contain PII or credentials (the executor may have
                     raised with sensitive data in its message — the use
                     case is responsible for sanitizing before calling
                     this constructor in that path).
            details: Optional structured payload (see class docstring).

        Example:
            Response.error(
                "TOOL_NOT_FOUND",
                "no tool registered with name 'foo'",
            )
        """
        return cls(
            is_ok=False,
            code=code,
            message=message,
            details=details,
        )


__all__ = ["Response"]
