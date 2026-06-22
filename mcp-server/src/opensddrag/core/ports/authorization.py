"""Authorization policy port.

Decides *whether* a caller may invoke a given tool, given the caller's
business-level `Permission` and the tool's `required_permission`. The
decision is a tagged union (`Allow` / `Deny(reason)` /
`RequireConfirmation(prompt)`) — see `core/domain/permission.py`.

The port is **stateless** from the use case's perspective. Every
implementation is a pure function of the inputs (no I/O, no lookup, no
time-of-day). The default implementation
(`DefaultAuthorizationPolicy` in `infrastructure/auth/authorization_policy.py`)
is `caller_permission >= tool.required_permission` in the
`READ_ONLY < WRITE < ADMIN` ordering; future implementations may
introduce per-tool overrides, time-of-day restrictions, or call-count
quotas — all without changing the use case.

This module is part of the **dependency-inversion seam** (core/ports/).
It MUST NOT import from any internal project module other than
`core.domain`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from opensddrag.core.domain.permission import (
    AuthorizationDecision,
    Permission,
)
from opensddrag.core.domain.tool import Tool


@runtime_checkable
class AuthorizationPolicyPort(Protocol):
    """Pure-function policy: caller_permission + tool -> decision."""

    def check(
        self,
        caller_permission: Permission,
        tool: Tool,
    ) -> AuthorizationDecision:
        """Return whether the caller may invoke the tool.

        Implementations MUST be pure functions of the inputs:
        * No I/O (no DB, no file, no network).
        * No logging side effects (logging is `LoggerPort`'s job).
        * No mutation of `tool` or any other state.

        The default implementation (`DefaultAuthorizationPolicy`)
        returns `Allow()` iff `caller_permission >= tool.required_permission`
        in the `READ_ONLY < WRITE < ADMIN` ordering, and `Deny(reason)`
        otherwise.

        Args:
            caller_permission: The `Permission` resolved by the
                `AuthenticationPort` for the current caller.
            tool: The `Tool` the caller wants to invoke. The port
                receives the full `Tool` (not just its
                `required_permission`) so future policies can override
                per-tool rules (e.g. "this specific tool requires
                `ADMIN` regardless of its declared `required_permission`").

        Returns:
            An `AuthorizationDecision`:
            * `Allow()` — the use case proceeds.
            * `Deny(reason)` — the use case returns
              `Response.error(code="FORBIDDEN", message=reason)` and
              does not call the executor.
            * `RequireConfirmation(prompt)` — the use case returns
              `Response.error(code="CONFIRMATION_REQUIRED", ...)` and
              does not call the executor. (Future work.)
        """
        ...


__all__ = ["AuthorizationPolicyPort"]
