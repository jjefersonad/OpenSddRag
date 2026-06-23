"""Unit tests for `PgLogger` — the structured stderr `LoggerPort`.

Spec refs:
    mcp-infrastructure-spec REQ-001 — "Structured JSON Logger": a
        `LoggerPort` implementation MUST emit single-line JSON with
        at minimum `timestamp`, `level`, `event` (plus the standard
        use-case fields). The default writer is `stderr`.

These tests capture stderr with `contextlib.redirect_stderr` and
parse each emitted line with `json.loads`. They do NOT touch
PostgreSQL — the logger only writes to a stream.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr
from datetime import datetime, timezone

from opensddrag.core.ports.logger import LoggerPort
from opensddrag.infrastructure.pg.pg_logger import PgLogger


def _capture(fn) -> dict:
    """Run `fn()` while capturing stderr, then parse the single line
    it emitted as JSON and return the resulting dict.
    """
    buffer = io.StringIO()
    with redirect_stderr(buffer):
        fn()
    output = buffer.getvalue()
    lines = [ln for ln in output.splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected exactly one log line, got {lines!r}"
    return json.loads(lines[0])


# ─── Test 1: info writes valid JSON ────────────────────────────────────────


def test_info_writes_valid_json() -> None:
    """`info()` MUST write one line of valid JSON to stderr with the
    `timestamp`, `level`, and `event` keys.
    """
    logger = PgLogger()
    record = _capture(lambda: logger.info("tool.executed"))

    assert record["level"] == "INFO"
    assert record["event"] == "tool.executed"
    assert "timestamp" in record
    # The timestamp parses as an ISO 8601 UTC datetime.
    parsed = datetime.fromisoformat(record["timestamp"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(None)


# ─── Test 2: warning includes level="WARNING" ──────────────────────────────


def test_warning_includes_warning_level() -> None:
    """`warning()` MUST tag the line with `level="WARNING"`."""
    logger = PgLogger()
    record = _capture(
        lambda: logger.warning("rate_limiter_fallback_to_memory")
    )
    assert record["level"] == "WARNING"
    assert record["event"] == "rate_limiter_fallback_to_memory"


# ─── Test 3: error includes level="ERROR" ──────────────────────────────────


def test_error_includes_error_level() -> None:
    """`error()` MUST tag the line with `level="ERROR"`."""
    logger = PgLogger()
    record = _capture(lambda: logger.error("tool.failed"))
    assert record["level"] == "ERROR"
    assert record["event"] == "tool.failed"


# ─── Test 4: extra fields are included ──────────────────────────────────────


def test_extra_fields_are_included() -> None:
    """The `**fields` passed by the use case MUST appear verbatim in
    the JSON payload alongside `timestamp`/`level`/`event`.
    """
    logger = PgLogger()
    record = _capture(
        lambda: logger.info(
            "tool.executed",
            tool_name="search_semantic",
            caller_id="stdio",
            duration_ms=12,
            result_status="ok",
        )
    )
    assert record["tool_name"] == "search_semantic"
    assert record["caller_id"] == "stdio"
    assert record["duration_ms"] == 12
    assert record["result_status"] == "ok"


# ─── Test 5 (bonus): non-JSON-native values serialize via default=str ──────


def test_non_json_native_values_serialize() -> None:
    """`json.dumps(payload, default=str)` MUST coerce datetimes,
    UUIDs, and enums to strings so serialization never fails on an
    exotic field value.
    """
    import uuid

    logger = PgLogger()
    artifact_id = uuid.uuid4()
    when = datetime.now(timezone.utc)
    record = _capture(
        lambda: logger.info(
            "tool.executed", artifact_id=artifact_id, when=when
        )
    )
    assert record["artifact_id"] == str(artifact_id)
    assert record["when"] == str(when)


# ─── Test 6 (bonus): satisfies the LoggerPort Protocol ─────────────────────


def test_satisfies_logger_port() -> None:
    """`PgLogger` MUST be a structural subtype of `LoggerPort`."""
    assert isinstance(PgLogger(), LoggerPort)


# ─── Test 7 (bonus): logging never raises ──────────────────────────────────


def test_logging_never_raises() -> None:
    """Per the `LoggerPort` contract, a write failure MUST be
    swallowed. We inject a stream whose `write` always raises and
    assert the call returns normally.
    """

    class _ExplodingStream:
        def write(self, _: str) -> int:
            raise OSError("disk full")

    logger = PgLogger(stream=_ExplodingStream())
    # MUST NOT raise.
    logger.info("tool.executed", tool_name="x")
    logger.warning("w")
    logger.error("e")
