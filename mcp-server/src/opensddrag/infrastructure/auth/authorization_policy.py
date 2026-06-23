"""Default `AuthorizationPolicyPort` — permission-ordering rule.

The default policy is the simplest useful one: a caller may invoke a
tool iff the caller's `Permission` is **at least** the tool's
`required_permission`, in the total order

    READ_ONLY < WRITE < ADMIN

The ordering is defined here (in `_PERMISSION_ORDER`) rather than on the
`Permission` enum itself: the enum is a `str, Enum` (so its `.value` is
human-readable in logs and JSON) and deliberately carries no business
logic — see `core/domain/permission.py`. The policy module is the
single place that knows how permissions compare.

The policy is a **pure function** of its inputs: no I/O, no logging, no
mutation. Future implementations may add per-tool overrides or
time-of-day restrictions without changing the use case (they only swap
the concrete `AuthorizationPolicyPort` in the composition root).

This module is part of the **infrastructure layer** (auth/
sub-package). It imports only from `core.domain.*` and `core.ports.*`.
It MUST NOT import from `mcp/`, `fastmcp`, `starlette`, `psycopg`, or
any `opensddrag.db.*` module.
"""

from __future__ import annotations

from opensddrag.core.domain.permission import (
    Allow,
    AuthorizationDecision,
    Deny,
    Permission,
)
from opensddrag.core.domain.tool import Tool

# Total order over the closed permission set. A caller may invoke a tool
# when `_PERMISSION_ORDER[caller] >= _PERMISSION_ORDER[required]`.
_PERMISSION_ORDER: dict[Permission, int] = {
    Permission.READ_ONLY: 0,
    Permission.WRITE: 1,
    Permission.ADMIN: 2,
}


class DefaultAuthorizationPolicy:
    """`AuthorizationPolicyPort` granting access by permission ordering.

    No-arg constructor: the policy holds no state, so a single instance
    can be shared across the whole process (the composition root builds
    one and injects it into the use case).
    """

    def __init__(self) -> None:
        # Stateless: nothing to configure. A no-arg constructor lets the
        # composition root instantiate the default policy uniformly.
        pass

    def check(
        self,
        caller_permission: Permission,
        tool: Tool,
    ) -> AuthorizationDecision:
        """Return `Allow()` iff the caller meets the tool's permission.

        `caller_permission >= tool.required_permission` in the
        `READ_ONLY < WRITE < ADMIN` ordering grants access; anything
        lower is denied with a human-readable, log-friendly reason.

        Pure function: no I/O, no logging, no mutation of `tool`.
        """
        if _PERMISSION_ORDER[caller_permission] >= _PERMISSION_ORDER[tool.required_permission]:
            return Allow()
        return Deny(
            reason=(
                f"permission {caller_permission.value} < "
                f"required {tool.required_permission.value}"
            )
        )


__all__ = ["DefaultAuthorizationPolicy"]
