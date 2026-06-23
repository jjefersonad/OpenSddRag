"""Postgres-backed `RateLimiterPort` with an in-memory fallback.

`PgRateLimiter` maintains a per-caller sliding window in the
`rate_limit_counters` table (created in migration
`005_rate_limit_counters.sql`). Each `allow(caller_id)` call runs a
single transaction:

    1. DELETE rows older than the window for this caller (prune).
    2. SELECT COUNT(*) of the caller's remaining rows.
    3. If the count is under quota: INSERT a new timestamp and return
       `(True, 0)`.
    4. Otherwise: compute `retry_after` (seconds until the oldest
       remaining row falls off the window) and return `(False, N)`.

If **any** database error occurs, the limiter logs a single
`rate_limiter_fallback_to_memory` warning via the injected
`LoggerPort` and then serves every subsequent call from an
in-memory `InMemoryRateLimiter` for the lifetime of the process
(see `mcp-infrastructure-spec` REQ-002 Scenario "Database outage
triggers fallback").

This module is part of the **infrastructure layer**
(`infrastructure/pg/`). Per the layer-dependency rule it MAY import
from `opensddrag.db.connection` (an infrastructure detail) and from
sibling infrastructure modules, but it MUST NOT import from `mcp/`,
`core/usecases/`, or `core/domain/`. It depends on the ports
(`core.ports.*`) only — the dependency-inversion seam.
"""

from __future__ import annotations

import math

from opensddrag.core.ports.logger import LoggerPort
from opensddrag.core.ports.rate_limiter import RateLimiterPort
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.memory.in_memory_rate_limiter import (
    InMemoryRateLimiter,
)
from opensddrag.infrastructure.pg.pg_logger import PgLogger


class PgRateLimiter:
    """Postgres sliding-window `RateLimiterPort` with memory fallback.

    Constructor parameters (keyword-only):
        quota:           Maximum calls per `caller_id` per
                         `window_seconds`. Default 60.
        window_seconds:  Length of the sliding window. Default 60 s.
        fallback:        The `RateLimiterPort` to delegate to when the
                         database is unreachable. Defaults to an
                         `InMemoryRateLimiter` configured with the same
                         `quota` and `window_seconds`.
        logger:          The `LoggerPort` used to emit the
                         `rate_limiter_fallback_to_memory` warning.
                         Defaults to `PgLogger()` (stderr JSON).

    Thread/async safety: `allow` is `async` and runs one DB
    transaction per call. The fallback flag is a simple boolean
    flipped once on first DB failure; OpenSddRag's server is
    single-threaded under asyncio, so no lock is needed.
    """

    def __init__(
        self,
        *,
        quota: int = 60,
        window_seconds: int = 60,
        fallback: RateLimiterPort | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        if quota < 1:
            raise ValueError(f"quota must be >= 1, got {quota}")
        if window_seconds < 1:
            raise ValueError(f"window_seconds must be >= 1, got {window_seconds}")
        self._quota = quota
        self._window_seconds = window_seconds
        self._fallback: RateLimiterPort = fallback or InMemoryRateLimiter(
            quota=quota, window_seconds=window_seconds
        )
        self._logger: LoggerPort = logger or PgLogger()
        # Once a DB error is seen we stay on the in-memory fallback for
        # the lifetime of the process (a flapping DB connection would
        # otherwise produce a warning on every call).
        self._use_fallback = False

    async def allow(self, caller_id: str) -> tuple[bool, int]:
        """Decide whether `caller_id` may make another call right now.

        Returns `(True, 0)` when under quota, `(False, retry_after)`
        when at quota. On a DB error, transparently delegates to the
        in-memory fallback (which returns the same shape).
        """
        if self._use_fallback:
            return await self._fallback.allow(caller_id)

        try:
            return await self._allow_via_db(caller_id)
        except Exception as exc:  # noqa: BLE001 — any DB failure => fallback
            # Flip to the fallback once and log a single warning. The
            # `LoggerPort` contract says logging never raises, so this
            # is safe even mid-failure.
            self._use_fallback = True
            self._logger.warning(
                "rate_limiter_fallback_to_memory",
                caller_id=caller_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return await self._fallback.allow(caller_id)

    async def _allow_via_db(self, caller_id: str) -> tuple[bool, int]:
        """Run the sliding-window logic in one PostgreSQL transaction.

        `get_conn()` yields a pooled connection whose work is committed
        when the context manager exits, so the DELETE/SELECT/INSERT
        below are atomic with respect to other callers.
        """
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                # 1. Prune entries older than the window for this caller.
                #    `make_interval(secs => %s)` keeps the window
                #    parameterized (an INTERVAL literal cannot be bound
                #    directly).
                await cur.execute(
                    "DELETE FROM rate_limit_counters "
                    "WHERE caller_id = %s "
                    "AND called_at < NOW() - make_interval(secs => %s)",
                    (caller_id, self._window_seconds),
                )

                # 2. Count the caller's remaining (in-window) calls.
                await cur.execute(
                    "SELECT COUNT(*) FROM rate_limit_counters WHERE caller_id = %s",
                    (caller_id,),
                )
                row = await cur.fetchone()
                count = row[0] if row else 0

                # 3. Under quota: record this call and allow it.
                if count < self._quota:
                    await cur.execute(
                        "INSERT INTO rate_limit_counters (caller_id) VALUES (%s)",
                        (caller_id,),
                    )
                    return True, 0

                # 4. At quota: compute seconds until the oldest entry
                #    falls off the window. `retry_after` is clamped to
                #    `>= 1` so the caller never hot-loops.
                await cur.execute(
                    "SELECT EXTRACT(EPOCH FROM "
                    "(MIN(called_at) + make_interval(secs => %s) - NOW())) "
                    "FROM rate_limit_counters WHERE caller_id = %s",
                    (self._window_seconds, caller_id),
                )
                retry_row = await cur.fetchone()
                seconds_left = retry_row[0] if retry_row and retry_row[0] is not None else self._window_seconds
                retry_after = max(1, math.ceil(float(seconds_left)))
                return False, retry_after


__all__ = ["PgRateLimiter"]
