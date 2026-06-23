"""Structured stderr logger — the default `LoggerPort` implementation.

Despite the historical `Pg` prefix, this logger does **not** touch
PostgreSQL. See `apply-clean-architecture-to-mcp-server-design.md`
Decision "`PgLogger` writes to stderr in JSON format, not to a DB
table": storing structured logs in the DB would couple the rate of
every tool call to the DB write throughput. Instead we write one
line of JSON to `sys.stderr` per call. Operators can redirect
stderr to a log aggregator (Loki, Datadog) without code changes.

Each log line is a single JSON object with at minimum:
    * `timestamp`     — ISO 8601 UTC (e.g. `2026-06-18T18:44:00.123456+00:00`)
    * `level`         — `"INFO"`, `"WARNING"`, or `"ERROR"`
    * `event`         — the stable dot-separated event name
    * plus any `**fields` the caller passes (the use case adds
      `tool_name`, `caller_id`, `duration_ms`, `result_status`,
      `error_code`).

Per the `LoggerPort` contract, the methods MUST NOT raise — a
logging failure is silently dropped (worst case: one line of
telemetry is lost; the caller's response is unaffected).

This module is part of the **infrastructure layer**
(`infrastructure/pg/`). It imports only stdlib (`sys`, `json`,
`datetime`) plus the `core.ports.*` seam. It MUST NOT import from
`mcp/`, `fastmcp`, `starlette`, `db/`, `embedding/`, or `config/`.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, TextIO

from opensddrag.core.ports.logger import LoggerPort


class PgLogger:
    """`LoggerPort` that writes one line of JSON per call to a stream.

    Constructor parameters:
        stream: The text stream to write to. Defaults to
            `sys.stderr`. Exposed so tests can inject a buffer
            and so operators can redirect output. The stream is
            captured lazily on each write (we read `sys.stderr`
            at call time when no explicit stream is given) so that
            `contextlib.redirect_stderr` works in tests.
    """

    def __init__(self, stream: TextIO | None = None) -> None:
        # `None` means "use whatever `sys.stderr` is at write time".
        # Keeping it lazy lets `contextlib.redirect_stderr` in tests
        # intercept the output without re-instantiating the logger.
        self._stream = stream

    def info(self, event: str, **fields: Any) -> None:
        """Emit a structured info event (`level="INFO"`)."""
        self._emit("INFO", event, fields)

    def warning(self, event: str, **fields: Any) -> None:
        """Emit a structured warning event (`level="WARNING"`)."""
        self._emit("WARNING", event, fields)

    def error(self, event: str, **fields: Any) -> None:
        """Emit a structured error event (`level="ERROR"`)."""
        self._emit("ERROR", event, fields)

    def _emit(self, level: str, event: str, fields: dict[str, Any]) -> None:
        """Serialize one log record and write it as a single line.

        `timestamp`, `level`, and `event` lead the payload; the
        caller's `**fields` follow. `json.dumps(..., default=str)`
        coerces non-JSON-native values (datetimes, UUIDs, enums)
        to their string form so serialization never fails on an
        exotic field value.

        The method swallows every exception: per the `LoggerPort`
        contract, a logging failure MUST NOT propagate to the
        caller.
        """
        try:
            payload: dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "event": event,
                **fields,
            }
            line = json.dumps(payload, default=str)
            stream = self._stream if self._stream is not None else sys.stderr
            stream.write(line + "\n")
        except Exception:  # noqa: BLE001 — logging is fire-and-forget
            # Telemetry is best-effort. Dropping one line is always
            # preferable to crashing the request that produced it.
            pass


__all__ = ["PgLogger"]
