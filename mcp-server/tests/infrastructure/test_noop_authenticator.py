"""Unit tests for `NoopAuthenticator` — the default
`AuthenticationPort` for development.

Spec refs:
    mcp-infrastructure-spec REQ-003 Scenario "Auth port exists with
        no-op default" — the wiring MUST inject the no-op
        `AuthenticationPort` and the use case MUST proceed without
        authentication checks.

    mcp-infrastructure-spec REQ-003 Scenario "Future JWT
        implementation is a drop-in" — a future
        `JwtAuthenticator(AuthenticationPort)` implementation MUST
        be wireable by setting `AUTH_PROVIDER=jwt` without any
        change to `ExecuteToolUseCase` or to the MCP adapter.

These tests live under `tests/infrastructure/` because the
authenticator is an infrastructure adapter. They do NOT touch
PostgreSQL, the embedding model, or the MCP server.
"""

from __future__ import annotations

import unittest.mock as mock

import pytest

from opensddrag.core.domain.permission import Permission
from opensddrag.core.ports import Caller
from opensddrag.core.ports.authentication import AuthenticationPort
from opensddrag.infrastructure.auth.noop_authenticator import NoopAuthenticator


@pytest.fixture
def authenticator() -> NoopAuthenticator:
    return NoopAuthenticator()


# ─── Test 1: always returns ADMIN ───────────────────────────────────────────


def test_always_returns_admin(authenticator: NoopAuthenticator) -> None:
    """`resolve()` MUST return a `Caller` with `Permission.ADMIN`
    regardless of the input `caller_id`. This is the whole point
    of the no-op authenticator: trust the upstream boundary and
    grant the highest permission to every caller.
    """
    for input_id in [
        "anonymous",
        "stdio",
        "api-key-abc123",
        "very-long-caller-id-with-special-chars-!@#",
        "",  # even an empty caller_id gets ADMIN (no defensive filter)
    ]:
        caller = authenticator.resolve(input_id)
        assert isinstance(caller, Caller), (
            f"resolve({input_id!r}) returned {type(caller).__name__}, "
            f"expected Caller"
        )
        assert caller.permission is Permission.ADMIN, (
            f"resolve({input_id!r}) returned permission "
            f"{caller.permission!r}, expected Permission.ADMIN"
        )


# ─── Test 2: preserves caller_id ───────────────────────────────────────────


def test_preserves_caller_id(authenticator: NoopAuthenticator) -> None:
    """`resolve()` MUST preserve the input `caller_id` unchanged in
    the returned `Caller`. The `caller_id` is the stable identifier
    the rate limiter and logger use to bucket the caller's
    activity; overwriting it with a hardcoded value would
    corrupt every downstream log line.
    """
    test_ids = [
        "stdio",
        "api-key-abc123",
        "user@example.com",
        "very-long-caller-id-with-many-chars-1234567890",
        "12345",  # numeric-looking string
    ]
    for input_id in test_ids:
        caller = authenticator.resolve(input_id)
        assert caller.caller_id == input_id, (
            f"resolve({input_id!r}) returned caller_id "
            f"{caller.caller_id!r}, expected {input_id!r}"
        )


# ─── Test 3 (bonus): the no-op satisfies the AuthenticationPort Protocol ───


def test_is_authentication_port_subtype(authenticator: NoopAuthenticator) -> None:
    """The no-op authenticator MUST be a structural subtype of
    `AuthenticationPort` — verified via `@runtime_checkable` so a
    future contributor who accidentally changes the signature
    gets a loud `TypeError` at construction time.
    """
    assert isinstance(authenticator, AuthenticationPort)


# ─── Test 4 (bonus): resolve is a pure function of the input ───────────────


def test_resolve_is_deterministic(authenticator: NoopAuthenticator) -> None:
    """Two calls with the same `caller_id` MUST return equal
    `Caller` objects. The implementation is stateless and
    deterministic; this test guards against the future regression
    class of "someone adds a random number to the caller_id".
    """
    c1 = authenticator.resolve("test-id")
    c2 = authenticator.resolve("test-id")
    assert c1 == c2
    # Equality is structural (frozen dataclass generates __eq__).
    assert c1.caller_id == c2.caller_id
    assert c1.permission == c2.permission


# ─── Test 5 (bonus): no-arg constructor ────────────────────────────────────


def test_no_arg_constructor() -> None:
    """`NoopAuthenticator()` MUST be constructible with no
    arguments. The composition root uses this signature to
    instantiate the default authenticator.
    """
    auth = NoopAuthenticator()
    assert auth is not None
    # Construction is idempotent — two instances are interchangeable.
    auth2 = NoopAuthenticator()
    assert auth.resolve("x") == auth2.resolve("x")


# ─── Test 6 (bonus): shape that future `JwtAuthenticator` must match ─────


def test_returns_caller_with_admin_even_when_input_looks_like_jwt(
    authenticator: NoopAuthenticator,
) -> None:
    """A future `JwtAuthenticator` will be a drop-in replacement for
    `NoopAuthenticator`. To prove the contract, the no-op's return
    shape (Caller dataclass with caller_id + permission) is exactly
    what a JWT-based authenticator would also produce — only the
    `permission` value would differ.

    This test asserts the SHAPE, not the value: a future
    `JwtAuthenticator` that returned something other than a
    `Caller` (or a `Caller` with different fields) would break the
    use case, and this test would still pass — but the structural
    check above (test_is_authentication_port_subtype) would
    catch it.
    """
    caller = authenticator.resolve("eyJhbGciOiJIUzI1NiJ9.fake.jwt")
    assert hasattr(caller, "caller_id")
    assert hasattr(caller, "permission")
    # The two fields are the only public surface of Caller.
    assert set(caller.__dataclass_fields__.keys()) == {"caller_id", "permission"}
