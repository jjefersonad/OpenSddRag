"""Unit tests for `DefaultAuthorizationPolicy`.

Spec refs:
    mcp-domain-core-spec REQ-002 — "Authorization policies as pure
        functions".
    apply-clean-architecture-to-mcp-server-design.md — Decision:
        "AuthorizationPolicyPort returns Allow / Deny / RequireConfirmation".

The policy is a pure function, so these tests touch no I/O — no
PostgreSQL, no MCP server.
"""

from __future__ import annotations

from opensddrag.core.domain.permission import (
    Allow,
    Deny,
    Permission,
)
from opensddrag.core.domain.tool import Tool
from opensddrag.core.ports.authorization import AuthorizationPolicyPort
from opensddrag.infrastructure.auth.authorization_policy import (
    DefaultAuthorizationPolicy,
)


def _tool(required: Permission) -> Tool:
    return Tool(
        name="t",
        description="a tool",
        required_permission=required,
        input_schema={"type": "object"},
        output_schema={},
    )


# ─── Test 1: admin can invoke a write tool ─────────────────────────────────


def test_admin_can_invoke_write_tool() -> None:
    """ADMIN (highest) may invoke a WRITE tool — Allow()."""
    policy = DefaultAuthorizationPolicy()
    decision = policy.check(Permission.ADMIN, _tool(Permission.WRITE))
    assert isinstance(decision, Allow)


# ─── Test 2: write cannot invoke an admin tool ─────────────────────────────


def test_write_cannot_invoke_admin_tool() -> None:
    """WRITE is below ADMIN, so invoking an ADMIN-only tool is denied."""
    policy = DefaultAuthorizationPolicy()
    decision = policy.check(Permission.WRITE, _tool(Permission.ADMIN))
    assert isinstance(decision, Deny)


# ─── Test 3: read-only can invoke a read-only tool ─────────────────────────


def test_read_only_can_invoke_read_only_tool() -> None:
    """Equal permission (READ_ONLY == READ_ONLY) is allowed."""
    policy = DefaultAuthorizationPolicy()
    decision = policy.check(Permission.READ_ONLY, _tool(Permission.READ_ONLY))
    assert isinstance(decision, Allow)


# ─── Test 4: Deny carries a human-readable reason ──────────────────────────


def test_deny_includes_human_reason() -> None:
    """`Deny.reason` MUST name both the caller permission and the
    required permission so a log line is self-explanatory.
    """
    policy = DefaultAuthorizationPolicy()
    decision = policy.check(Permission.READ_ONLY, _tool(Permission.WRITE))
    assert isinstance(decision, Deny)
    assert "READ_ONLY" in decision.reason
    assert "WRITE" in decision.reason
    # Sanity: the reason reads as "permission X < required Y".
    assert "<" in decision.reason


# ─── Test 5 (bonus): satisfies the AuthorizationPolicyPort Protocol ────────


def test_satisfies_authorization_policy_port() -> None:
    """`DefaultAuthorizationPolicy` MUST be a structural subtype of
    `AuthorizationPolicyPort`.
    """
    assert isinstance(DefaultAuthorizationPolicy(), AuthorizationPolicyPort)


# ─── Test 6 (bonus): full ordering matrix ──────────────────────────────────


def test_full_permission_ordering_matrix() -> None:
    """Exhaustively verify READ_ONLY < WRITE < ADMIN: a caller is
    allowed iff its permission rank is >= the tool's.
    """
    policy = DefaultAuthorizationPolicy()
    order = [Permission.READ_ONLY, Permission.WRITE, Permission.ADMIN]
    for caller_idx, caller in enumerate(order):
        for required_idx, required in enumerate(order):
            decision = policy.check(caller, _tool(required))
            if caller_idx >= required_idx:
                assert isinstance(decision, Allow), (
                    f"{caller} should invoke a {required} tool"
                )
            else:
                assert isinstance(decision, Deny), (
                    f"{caller} should NOT invoke a {required} tool"
                )
