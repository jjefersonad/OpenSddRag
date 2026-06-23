"""In-memory `RateLimiterPort` — the fallback path for tests and for
the `RATE_LIMITER=memory` configuration.

A sliding window of timestamps is kept per `caller_id` in an
in-process dict. On every `allow(caller_id)` call:

    1. Drop timestamps older than `now() - window_seconds`.
    2. If the remaining count is `< quota`, append `now()` and
       return `(True, 0)`.
    3. Otherwise return `(False, retry_after_seconds)` where
       `retry_after_seconds = ceil(window_end - now())` and
       `window_end = oldest_remaining_timestamp + window_seconds`
       (the moment when the oldest entry will fall off the window
       and a new call will be allowed).

This implementation is **not** shared across processes — each
process has its own counter dict. In production the
`PgRateLimiter` (in `infrastructure/pg/pg_rate_limiter.py`) is
preferred because its counters are visible to all worker
processes behind the same load balancer.

This module is part of the **infrastructure layer**
(`infrastructure/memory/`). It imports only from `core.ports.*`
and `core.domain.*`. It MUST NOT import from `mcp/`, `db/`,
`embedding/`, `cli/`, `config/`, `models/`, or any other
infrastructure sub-package (notably `infrastructure/pg/`,
which would defeat the purpose of this fallback path).
"""

from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from typing import Deque

from opensddrag.core.ports.rate_limiter import RateLimiterPort


# Default quota and window. Matches the spec's `mcp-infrastructure-spec`
# REQ-002 "sliding window of 60 seconds and a configurable per-profile
# quota". The defaults are 60 calls per 60 seconds — i.e. 1 call per
# second on average. These are deliberately conservative; a future
# change may make them per-profile configurable.
DEFAULT_QUOTA: int = 60
DEFAULT_WINDOW_SECONDS: int = 60


class InMemoryRateLimiter:
    """Process-local sliding-window `RateLimiterPort`.

    Constructor parameters:
        quota:           Maximum number of calls per `caller_id`
                         per `window_seconds`. Default 60.
        window_seconds:  Length of the sliding window. Default 60 s.
        clock:           Callable that returns the current time in
                         seconds (a `monotonic` clock). Default
                         `time.monotonic`. Exposed as a parameter so
                         tests can inject a fake clock to test the
                         "slides window" behavior without sleeping.

    Thread safety: the implementation is **not** thread-safe
    (no locks). OpenSddRag's MCP server runs single-threaded
    under asyncio, so this is sufficient. A multi-threaded
    deployment would need a lock around `allow` — out of scope
    for this change.
    """

    def __init__(
        self,
        *,
        quota: int = DEFAULT_QUOTA,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        clock: callable = time.monotonic,
    ) -> None:
        if quota < 1:
            raise ValueError(f"quota must be >= 1, got {quota}")
        if window_seconds < 1:
            raise ValueError(f"window_seconds must be >= 1, got {window_seconds}")
        self._quota = quota
        self._window_seconds = window_seconds
        self._clock = clock
        # `dict[str, deque[float]]` — one deque per caller. We use
        # `defaultdict` so the lookup is implicit. `deque` with an
        # unbounded `maxlen` is the right structure: O(1) `append`
        # and O(k) `popleft` where k is the number of expired
        # entries (typically 0 or 1).
        self._timestamps: dict[str, Deque[float]] = defaultdict(deque)

    async def allow(self, caller_id: str) -> tuple[bool, int]:
        """Decide whether the caller may make another call right now.

        Declared `async` to satisfy the `RateLimiterPort` contract (the
        Postgres adapter does async I/O); this implementation does no
        awaiting — all state is in-process.

        Args:
            caller_id: Opaque stable identifier for the caller. The
                limiter keys its counter dict on this value, so the
                identifier MUST be stable across calls.

        Returns:
            A `(allowed, retry_after_seconds)` tuple:
            * `(True, 0)` — under quota, proceed.
            * `(False, N)` — over quota; `N` is the number of
              seconds the caller should wait before retrying
              (always `>= 1` when `allowed=False`, per the spec
              contract).
        """
        now = self._clock()
        # A timestamp at exactly `now - window_seconds` is at the
        # boundary: it has aged out of the window. The strict `<`
        # in the loop body is correct; the boundary timestamp is
        # removed on the next call (or this one, if the next
        # check were `<=`). The standard "sliding window of N
        # seconds" interpretation is: timestamps with
        # `timestamp > now - window_seconds` count; timestamps with
        # `timestamp <= now - window_seconds` do not.
        window_start = now - self._window_seconds
        timestamps = self._timestamps[caller_id]

        # Step 1: drop expired entries (older than or equal to
        # `window_start`). The deque is ordered chronologically
        # (oldest at the left, newest at the right) so we can
        # popleft while the leftmost entry is expired.
        while timestamps and timestamps[0] <= window_start:
            timestamps.popleft()

        # Step 2: under-quota path.
        if len(timestamps) < self._quota:
            timestamps.append(now)
            return True, 0

        # Step 3: at-quota path. Compute `retry_after` as the
        # number of seconds until the oldest entry expires. We
        # use `math.ceil` so the caller always waits at least 1
        # second (a `retry_after=0` would invite a hot loop).
        oldest = timestamps[0]
        window_end = oldest + self._window_seconds
        retry_after = max(1, math.ceil(window_end - now))
        return False, retry_after


__all__ = [
    "DEFAULT_QUOTA",
    "DEFAULT_WINDOW_SECONDS",
    "InMemoryRateLimiter",
]
