"""Unit tests for `InMemoryRateLimiter`.

Spec refs:
    mcp-infrastructure-spec REQ-002 Scenario "Caller exceeding quota
        is rejected" and "Database outage triggers fallback" — the
        fallback `InMemoryRateLimiter` is selected when the DB is
        unreachable (or by `RATE_LIMITER=memory`).

These tests live under `tests/infrastructure/` because the rate
limiter is an infrastructure adapter. They do NOT touch
PostgreSQL — the implementation is pure in-process state.
"""

from __future__ import annotations

import pytest

from opensddrag.core.ports.rate_limiter import RateLimiterPort
from opensddrag.infrastructure.memory.in_memory_rate_limiter import InMemoryRateLimiter


# ─── Test 1: allows when under quota ────────────────────────────────────────


async def test_allows_when_under_quota() -> None:
    """A caller that has made fewer than `quota` calls in the last
    `window_seconds` is allowed. Each call records a timestamp and
    returns `(True, 0)`.
    """
    # Fake clock so the test is deterministic.
    clock_value = [1000.0]

    def clock() -> float:
        return clock_value[0]

    rl = InMemoryRateLimiter(quota=3, window_seconds=60, clock=clock)

    for i in range(3):
        allowed, retry = await rl.allow("alice")
        assert allowed is True
        assert retry == 0
        clock_value[0] += 1.0  # 1 second between calls


# ─── Test 2: denies when at quota ──────────────────────────────────────────


async def test_denies_when_at_quota() -> None:
    """A caller that has made `quota` calls in the window is denied.
    The 4th call (when `quota=3`) returns `(False, retry_after)`
    with `retry_after > 0`.
    """
    rl = InMemoryRateLimiter(quota=3, window_seconds=60)

    for _ in range(3):
        allowed, _ = await rl.allow("alice")
        assert allowed

    allowed, retry = await rl.allow("alice")
    assert allowed is False
    assert retry > 0


# ─── Test 3: slides the window after `window_seconds` ──────────────────────


async def test_slides_window_after_window_seconds() -> None:
    """After advancing the clock by `window_seconds`, the oldest
    timestamp is no longer in the window and a new call is allowed.
    """
    clock_value = [1000.0]
    rl = InMemoryRateLimiter(quota=2, window_seconds=60, clock=lambda: clock_value[0])

    # Fill the bucket.
    await rl.allow("alice")
    await rl.allow("alice")
    allowed, _ = await rl.allow("alice")
    assert allowed is False  # 3rd call: over quota

    # Advance the clock by exactly `window_seconds` (boundary).
    clock_value[0] += 60.0
    allowed, _ = await rl.allow("alice")
    assert allowed is True, (
        "After advancing the clock by `window_seconds`, the oldest "
        "timestamp is at the boundary and should be removed; the "
        "next call should be allowed."
    )

    # Advance further: the previous call (at clock=1060) is also
    # at the boundary now. A new call is allowed.
    clock_value[0] += 60.0
    allowed, _ = await rl.allow("alice")
    assert allowed is True

    # The new call added a 2nd timestamp in the new window
    # (clock=1120). One more call right now (clock=1120) would
    # also be allowed (1 < quota=2), and the one after that
    # would be denied (2 == quota=2). Verify the boundary is
    # exactly at 2 in the new window.
    allowed, _ = await rl.allow("alice")
    assert allowed is True
    allowed, _ = await rl.allow("alice")
    assert allowed is False, (
        "After 2 calls in the new window, the 3rd should be denied "
        "(quota=2)"
    )


# ─── Test 4: returns positive `retry_after` when denied ───────────────────


async def test_returns_positive_retry_after_when_denied() -> None:
    """When denied, `retry_after` MUST be in `[1, window_seconds]`
    (per `RateLimiterPort` contract). It is `0` only when the call
    is allowed.
    """
    rl = InMemoryRateLimiter(quota=1, window_seconds=60)

    allowed, retry = await rl.allow("alice")
    assert allowed and retry == 0

    # Denied — `retry_after` is positive.
    allowed, retry = await rl.allow("alice")
    assert not allowed
    assert 1 <= retry <= 60, (
        f"retry_after must be in [1, 60] when denied, got {retry}"
    )


# ─── Test 5 (bonus): different callers have independent buckets ───────────


async def test_different_callers_have_independent_buckets() -> None:
    """The limiter MUST key its counter dict on `caller_id` so two
    callers do not share quotas.
    """
    rl = InMemoryRateLimiter(quota=2, window_seconds=60)

    # alice fills her bucket.
    await rl.allow("alice")
    await rl.allow("alice")
    allowed, _ = await rl.allow("alice")
    assert not allowed

    # bob is unaffected.
    allowed, _ = await rl.allow("bob")
    assert allowed


# ─── Test 6 (bonus): satisfies the RateLimiterPort Protocol ──────────────


def test_satisfies_rate_limiter_port() -> None:
    """`InMemoryRateLimiter` MUST be a structural subtype of
    `RateLimiterPort` (verified via `@runtime_checkable`).
    """
    rl = InMemoryRateLimiter(quota=10, window_seconds=60)
    assert isinstance(rl, RateLimiterPort)


# ─── Test 7 (bonus): invalid constructor arguments raise ────────────────


def test_invalid_constructor_arguments_raise() -> None:
    """`quota < 1` and `window_seconds < 1` MUST raise `ValueError`
    so a misconfiguration is caught at startup, not at the first
    `allow()` call.
    """
    with pytest.raises(ValueError):
        InMemoryRateLimiter(quota=0, window_seconds=60)
    with pytest.raises(ValueError):
        InMemoryRateLimiter(quota=10, window_seconds=0)
    with pytest.raises(ValueError):
        InMemoryRateLimiter(quota=-1, window_seconds=60)
    with pytest.raises(ValueError):
        InMemoryRateLimiter(quota=10, window_seconds=-5)
