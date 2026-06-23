"""Integration tests for `PgRateLimiter` sliding-window semantics.

These tests hit the real PostgreSQL `rate_limit_counters` table (migration
005) via the session-scoped `db_pool` fixture in the root `conftest.py`.
They use static caller IDs ("alice", "bob") and rely on the
`truncate_rate_limit_counters` fixture from the local `conftest.py` to
guarantee a clean table before each test.

Skipped automatically when PostgreSQL is not reachable so the suite
does not fail on a developer machine without Docker running.
"""

from __future__ import annotations

import os

import psycopg
import pytest

from opensddrag.infrastructure.pg.pg_rate_limiter import PgRateLimiter

# ── DB reachability guard ─────────────────────────────────────────────────────

_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://opensddrag:opensddrag@localhost:54326/opensddrag",
)


@pytest.fixture(autouse=True, scope="module")
def require_db() -> None:
    """Skip the whole module when PostgreSQL is not reachable."""
    try:
        with psycopg.connect(_DB_URL, connect_timeout=3):
            pass
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL not reachable — start docker compose up -d")


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pg_rate_limiter_allows_under_quota(
    truncate_rate_limit_counters,
) -> None:
    """Three calls under a quota of 3 must all return (True, 0)."""
    rl = PgRateLimiter(quota=3, window_seconds=60)
    for _ in range(3):
        allowed, retry_after = await rl.allow("alice")
        assert allowed is True
        assert retry_after == 0


@pytest.mark.asyncio
async def test_pg_rate_limiter_denies_over_quota(
    truncate_rate_limit_counters,
) -> None:
    """The fourth call under a quota of 3 must be denied with 0 < retry_after <= 60."""
    rl = PgRateLimiter(quota=3, window_seconds=60)
    for _ in range(3):
        allowed, _ = await rl.allow("bob")
        assert allowed is True

    allowed, retry_after = await rl.allow("bob")
    assert allowed is False
    assert 0 < retry_after <= 60
