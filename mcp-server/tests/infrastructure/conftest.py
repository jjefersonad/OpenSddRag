"""Fixtures shared across tests/infrastructure/.

`truncate_rate_limit_counters` provides a clean slate for any test that
uses static caller IDs (e.g. "alice", "bob") and would otherwise
accumulate rows across test runs inside a session.
"""

from __future__ import annotations

import pytest

from opensddrag.db.connection import get_conn


@pytest.fixture
async def truncate_rate_limit_counters() -> None:
    """Truncate `rate_limit_counters` before and after each requesting test."""
    async with get_conn() as conn:
        await conn.execute("TRUNCATE TABLE rate_limit_counters")
    yield
    async with get_conn() as conn:
        await conn.execute("TRUNCATE TABLE rate_limit_counters")
