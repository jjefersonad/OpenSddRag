"""Domain permissions and authorization decisions.

This module is part of the **pure domain layer** (core/domain/) of the
OpenSddRag MCP server. It MUST NOT import from `mcp`, `fastmcp`, `starlette`,
`psycopg`, `pydantic_settings`, `sentence_transformers`, or any internal
project module (db/, embedding/, cli/, mcp/, config/, models/, infrastructure/).
Only the Python standard library is allowed.

See:
    - `mcp-domain-core-spec`        — REQ-002 (Authorization policies as pure functions)
    - `apply-clean-architecture-to-mcp-server-design.md` — Decision:
      "AuthorizationPolicyPort" returns one of `Allow` / `Deny` / `RequireConfirmation`
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Permission(str, Enum):
    """The closed set of business-level permissions in OpenSddRag.

    Stored in `api_keys.permission` (migration 006) as the string value
    (`'READ_ONLY' | 'WRITE' | 'ADMIN'`). The ordering is total and
    ascending: `READ_ONLY < WRITE < ADMIN`. A caller with permission P may
    invoke any tool whose `required_permission` is `<= P` (see
    `infrastructure/auth/authorization_policy.py` for the concrete rule).

    Using `str, Enum` (rather than `IntEnum`) means:

    1. The `.value` is human-readable in `psql` output and log lines.
    2. JSON serialization round-trips via the string, not an integer.
    3. The ordering used by the policy lives in the policy module
       (`_PERMISSION_ORDER`), not in the enum itself — keeping this
       module free of business logic (REQ-001 of mcp-domain-core-spec:
       "domain types are pure data").
    """

    READ_ONLY = "READ_ONLY"
    WRITE = "WRITE"
    ADMIN = "ADMIN"


# ── Tagged union: AuthorizationDecision ──────────────────────────────────────
#
# A tagged union (sum type) implemented as one abstract base + three dataclass
# variants. Each variant carries exactly the data its name suggests. The
# `kind` field on each variant lets external code branch without isinstance
# (e.g. for logging or JSON serialization). The `_ALLOWED_KINDS` frozenset
# guards against typos in the `kind=` field of new variants.


_ALLOWED_KINDS = frozenset({"allow", "deny", "require_confirmation"})


@dataclass(frozen=True)
class Allow:
    """Authorization granted. No payload."""

    kind: Literal["allow"] = "allow"


@dataclass(frozen=True)
class Deny:
    """Authorization denied. `reason` is a human-readable, log-friendly string.

    Examples: "permission READ_ONLY < required WRITE", "tool not in registry".
    The MCP adapter surfaces the reason as the `message` of a
    `Response.error(code="FORBIDDEN", message=reason)` (see
    tool-execution-usecase-spec REQ-001 Scenario "Authorization denied").
    """

    reason: str
    kind: Literal["deny"] = "deny"


@dataclass(frozen=True)
class RequireConfirmation:
    """Authorization requires explicit caller confirmation before proceeding.

    Not used by the current default policy (which is binary allow/deny), but
    declared here so future policies (e.g. destructive tools that need a
    second factor) have a first-class return type. The MCP adapter will
    surface this as `Response.error(code="CONFIRMATION_REQUIRED", ...)` —
    the wire format and the use-case handling are out of scope for this
    change and tracked as a follow-up.
    """

    prompt: str
    kind: Literal["require_confirmation"] = "require_confirmation"


# Union type alias — useful for `isinstance` checks in tests and for typing
# the return of `AuthorizationPolicyPort.check`.
AuthorizationDecision = Allow | Deny | RequireConfirmation


def is_allowed(decision: AuthorizationDecision) -> bool:
    """Return True iff `decision` is an `Allow`.

    `RequireConfirmation` returns False: the caller has not yet been
    authorized, only prompted. The use case must reject the call with
    `code="CONFIRMATION_REQUIRED"` and ask for explicit re-submission
    (future work).
    """
    return isinstance(decision, Allow)


__all__ = [
    "ALLOWED_KINDS",  # intentionally a module-level re-export of `_ALLOWED_KINDS`
    "Allow",
    "AuthorizationDecision",
    "Deny",
    "Permission",
    "RequireConfirmation",
    "is_allowed",
]

# Re-export the frozenset under a non-underscore name so it can be imported
# from outside the module without the convention violation.
ALLOWED_KINDS = _ALLOWED_KINDS
