"""Domain `Request` value object.

A `Request` is the use-case-level description of a single tool invocation:
the tool name, the raw parameters dict, and the caller's identity. The
`ExecuteToolUseCase.execute()` method (see core/usecases/execute_tool.py)
accepts a `Request` (or its constituent fields — see tool-execution-
usecase-spec REQ-001 for the exact signature) and returns a `Response`.

This module is part of the **pure domain layer** (core/domain/). It MUST
NOT import from `mcp`, `fastmcp`, `starlette`, `psycopg`, `pydantic_settings`,
`sentence_transformers`, or any internal project module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opensddrag.core.domain.permission import Permission


@dataclass(frozen=True)
class Request:
    """A single tool invocation, as seen by the use case.

    Fields:
        tool_name:  The name passed by the caller (matches `Tool.name`).
                    Unknown names are handled by the use case
                    (`Response.error(code="TOOL_NOT_FOUND")`) and never
                    raise here.
        parameters: The raw, unvalidated input dict from the caller. The
                    use case runs `InputValidatorPort.validate` against
                    `Tool.input_schema` before any execution.
        caller_id:  Stable opaque identifier for the caller — the API key
                    hash prefix in the HTTP path, `"stdio"` for the local
                    transport. Used by the rate limiter (`RateLimiterPort.allow`)
                    and tagged on every log line emitted by the use case.
        permission: The business-level permission resolved from the auth
                    port. The use case does NOT call `AuthorizationPolicyPort`
                    with anything other than this value (the policy is
                    consulted by passing the `permission` and the `Tool`).
    """

    tool_name: str
    parameters: dict[str, Any]
    caller_id: str
    permission: Permission


__all__ = ["Request"]
