"""Rate limiter port.

Per-caller sliding-window rate limiter. The use case calls `allow(caller_id)`
**after** authentication resolve and **before** input validation. The port
returns `(allowed, retry_after_seconds)`:
    * `allowed == True`  — the call is within the quota; the use case
      proceeds.
    * `allowed == False` — the call is over the quota; the use case
      returns `Response.error(code="RATE_LIMITED", details={"retry_after":
      retry_after_seconds})` and does not call the executor.

The reference implementation is `PgRateLimiter`
(`infrastructure/pg/pg_rate_limiter.py`) which persists per-caller
counters in the `rate_limit_counters` table (created in migration 005)
and falls back to `InMemoryRateLimiter` on DB outage. A Redis-backed
implementation can be added later as a drop-in replacement.

The port is **stateless from the use case's perspective** but the
implementation holds state (in-memory dict or DB rows). The state is
process-local in the in-memory case and shared across processes in the
Postgres case (which is the right model for a multi-worker server).

This module is part of the **dependency-inversion seam** (core/ports/).
It MUST NOT import from any internal project module.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RateLimiterPort(Protocol):
    """Per-caller sliding-window rate limiter."""

    async def allow(self, caller_id: str) -> tuple[bool, int]:
        """Decide whether the caller may make another call right now.

        Coroutine: the reference implementation (`PgRateLimiter`)
        performs async DB I/O. In-memory implementations are still
        declared `async` (they simply `return` without awaiting) so the
        use case can `await` the port uniformly regardless of which
        adapter is wired.

        Args:
            caller_id: Opaque stable identifier for the caller. The
                limiter keys its counter dict on this value, so the
                identifier MUST be stable across calls (the adapter
                derives it from the API key hash or the transport
                name).

        Returns:
            A `(allowed, retry_after_seconds)` tuple:
            * `(True, 0)` — under quota, proceed.
            * `(False, N)` — over quota; `N` is the number of seconds
              the caller should wait before retrying. The use case
              surfaces `N` in `Response.details["retry_after"]` and the
              MCP adapter maps it to a structured error. `N` MUST be
              in the range `[1, window_seconds]` (typically
              `[1, 60]` for the default 60-second window) — never `0`
              when `allowed == False`.

        Implementations MUST NOT raise. A backend outage is handled
        internally (the `PgRateLimiter` falls back to
        `InMemoryRateLimiter`; the use case sees a normal `allow`
        return value).
        """
        ...


__all__ = ["RateLimiterPort"]
