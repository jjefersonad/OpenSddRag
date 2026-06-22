"""Authentication port (use-case level).

This is the **use-case-level** auth port. It is **orthogonal to** the
HTTP `AuthMiddleware` in `opensddrag/mcp/auth.py` (which is transport-level
and validates a `Bearer` token from a request header against the
`api_keys` table). The two coexist on purpose:

  * The HTTP `AuthMiddleware` rejects requests with bad/missing/expired
    API keys **before** the request reaches the MCP adapter.
  * The use-case `AuthenticationPort` resolves the caller's *business-level*
    `Permission` from the caller's opaque `caller_id` (set by the adapter
    from `request.state.project_slug` for HTTP, or `"stdio"` for stdio).

A future OAuth/JWT implementation will replace the no-op default with a
real implementation that resolves the caller's permissions from a JWT
claim. The no-op default returns `Permission.ADMIN` for every caller, so
the use case works in development without any auth subsystem in place.

This module is part of the **dependency-inversion seam** (core/ports/).
It MUST NOT import from any internal project module (db/, embedding/,
cli/, mcp/, config/, models/, infrastructure/) other than `core.domain`,
which carries the pure `Permission` enum.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from opensddrag.core.domain.permission import Permission


@dataclass(frozen=True)
class Caller:
    """The identity of a single tool invocation, as seen by the use case.

    Fields:
        caller_id:  Stable opaque identifier for the caller — the API key
                    hash prefix in the HTTP path, `"stdio"` for the local
                    transport. Used by the rate limiter
                    (`RateLimiterPort.allow`) and tagged on every log
                    line emitted by the use case. Never a secret.
        permission: Business-level permission resolved from the auth
                    port. The use case passes this to
                    `AuthorizationPolicyPort.check(caller_permission, tool)`
                    to decide whether the call is allowed.

    The `Caller` is the single argument the use case needs to make
    *every* authorization, rate-limiting, and logging decision. See
    `apply-clean-architecture-to-mcp-server-design.md` Decision:
    "`ExecuteToolUseCase` carries a `Caller` object, not just `Permission`".
    """

    caller_id: str
    permission: Permission


@runtime_checkable
class AuthenticationPort(Protocol):
    """Resolves a `Caller` from a `caller_id`.

    The port is **stateless from the use case's perspective**: the use
    case calls `resolve(caller_id)` once per invocation and gets back a
    fresh `Caller`. Implementations may cache, may consult a database,
    or may always return the same synthetic `Caller` (the no-op default).

    Implementations MUST NOT raise. If the caller cannot be resolved,
    return a `Caller` with `permission=Permission.READ_ONLY` (the most
    restrictive safe default) — the use case will then either allow the
    call (if the tool requires only `READ_ONLY`) or reject it via the
    `AuthorizationPolicyPort`. This is a deliberate choice: the auth port
    has *no opinion* on whether the call is allowed; the policy port
    does.
    """

    def resolve(self, caller_id: str) -> Caller:
        """Resolve a `Caller` from a `caller_id`.

        Args:
            caller_id: Opaque stable identifier. For the HTTP path this
                is `api_key_hash[:12]` (set by the adapter); for stdio
                it is the literal string `"stdio"`. Never empty, never
                `None`.

        Returns:
            A `Caller` with a `permission` that the implementation
            derived from the caller. The default no-op implementation
            returns `Permission.ADMIN` regardless of input.
        """
        ...


__all__ = ["AuthenticationPort", "Caller"]
