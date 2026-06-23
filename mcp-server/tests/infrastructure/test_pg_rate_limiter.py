"""Tests for `PgRateLimiter` — the Postgres sliding-window rate limiter.

Spec refs:
    mcp-infrastructure-spec REQ-002 — "Rate Limiter with PostgreSQL
        Persistence and In-Memory Fallback".
        Scenario "Caller within quota is allowed"
        Scenario "Caller exceeding quota is rejected"
        Scenario "Database outage triggers fallback"

The first two tests are integration tests: they hit the real
PostgreSQL test database (the `rate_limit_counters` table created by
migration 005) via the session-scoped `db_pool` fixture in
`conftest.py`. Each uses a unique `caller_id` and cleans up its rows
on teardown so runs are isolated.

The third test is a pure unit test: it monkeypatches `get_conn` to
raise, then asserts the limiter logs `rate_limiter_fallback_to_memory`
and serves the call from the injected in-memory fallback.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.memory.in_memory_rate_limiter import (
    InMemoryRateLimiter,
)
from opensddrag.infrastructure.pg import pg_rate_limiter
from opensddrag.infrastructure.pg.pg_rate_limiter import PgRateLimiter


@pytest.fixture
def caller_id():
    """A unique caller id per test, with row cleanup on teardown."""
    cid = f"test-rl-{uuid4().hex[:12]}"
    yield cid


async def _cleanup(cid: str) -> None:
    async with get_conn() as conn:
        await conn.execute(
            "DELETE FROM rate_limit_counters WHERE caller_id = %s", (cid,)
        )


# ─── Test 1 (integration): allows when under quota ─────────────────────────


@pytest.mark.asyncio
async def test_allows_under_quota(caller_id) -> None:
    """A caller below quota is allowed on every call, each returning
    `(True, 0)`, and a row is recorded per allowed call.
    """
    rl = PgRateLimiter(quota=3, window_seconds=60)
    try:
        for _ in range(3):
            allowed, retry = await rl.allow(caller_id)
            assert allowed is True
            assert retry == 0

        # Three allowed calls -> three rows for this caller.
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM rate_limit_counters WHERE caller_id = %s",
                    (caller_id,),
                )
                count = (await cur.fetchone())[0]
        assert count == 3
    finally:
        await _cleanup(caller_id)


# ─── Test 2 (integration): denies when over quota ──────────────────────────


@pytest.mark.asyncio
async def test_denies_over_quota(caller_id) -> None:
    """Once the caller reaches quota, the next call is denied with a
    positive `retry_after`, and no extra row is recorded.
    """
    rl = PgRateLimiter(quota=2, window_seconds=60)
    try:
        assert (await rl.allow(caller_id))[0] is True
        assert (await rl.allow(caller_id))[0] is True

        allowed, retry = await rl.allow(caller_id)
        assert allowed is False
        assert 1 <= retry <= 60

        # The denied call MUST NOT have recorded an additional row.
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM rate_limit_counters WHERE caller_id = %s",
                    (caller_id,),
                )
                count = (await cur.fetchone())[0]
        assert count == 2, "denied call must not insert a row"
    finally:
        await _cleanup(caller_id)


# ─── Test 3 (unit): DB outage triggers fallback ────────────────────────────


class _FakeLogger:
    """Captures structured log calls for assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def info(self, event: str, **fields) -> None:
        self.calls.append(("INFO", event, fields))

    def warning(self, event: str, **fields) -> None:
        self.calls.append(("WARNING", event, fields))

    def error(self, event: str, **fields) -> None:
        self.calls.append(("ERROR", event, fields))


@pytest.mark.asyncio
async def test_db_outage_triggers_fallback(monkeypatch) -> None:
    """When the DB raises, the limiter MUST log
    `rate_limiter_fallback_to_memory` (once) and serve the call — and
    every subsequent call — from the in-memory fallback.
    """

    def _boom(*_args, **_kwargs):
        raise ConnectionError("simulated DB outage")

    # Make any DB access in the limiter explode.
    monkeypatch.setattr(pg_rate_limiter, "get_conn", _boom)

    logger = _FakeLogger()
    fallback = InMemoryRateLimiter(quota=1, window_seconds=60)
    rl = PgRateLimiter(
        quota=10, window_seconds=60, fallback=fallback, logger=logger
    )

    # First call: DB explodes -> fallback used. The fallback has
    # quota=1, so this call is allowed.
    allowed, retry = await rl.allow("alice")
    assert allowed is True
    assert retry == 0

    # The warning was logged exactly once with the right event name.
    warnings = [c for c in logger.calls if c[1] == "rate_limiter_fallback_to_memory"]
    assert len(warnings) == 1
    assert warnings[0][0] == "WARNING"

    # Second call: stays on the fallback (no new warning). The fallback
    # quota=1 is now exhausted, so this call is denied.
    allowed, retry = await rl.allow("alice")
    assert allowed is False
    assert retry >= 1

    # Still exactly one fallback warning — we do not re-log on every call.
    warnings = [c for c in logger.calls if c[1] == "rate_limiter_fallback_to_memory"]
    assert len(warnings) == 1
