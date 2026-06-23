"""Unit tests for the composition root `build_use_cases`.

Spec refs:
    apply-clean-architecture-to-mcp-server-design.md — Decision:
        "Use a single composition root infrastructure/composition.py".

These tests construct the use cases with a fake settings object. No
adapter performs I/O at construction time (PgRateLimiter does not
connect until `allow()`, PgToolRegistry metadata is static), so the
tests need no database.

Note on the wiring assertion: task-composition-1 text says
`execute_tool._registry`, but the implemented `ExecuteToolUseCase`
stores the registry as `_tool_registry` (see core/usecases/execute_tool.py).
We assert against the real attribute name.
"""

from __future__ import annotations

from types import SimpleNamespace

from opensddrag.core.usecases.execute_tool import ExecuteToolUseCase
from opensddrag.core.usecases.list_tools import ListToolsUseCase
from opensddrag.infrastructure.composition import UseCases, build_use_cases
from opensddrag.infrastructure.memory.in_memory_rate_limiter import (
    InMemoryRateLimiter,
)
from opensddrag.infrastructure.memory.in_memory_tool_registry import (
    InMemoryToolRegistry,
)
from opensddrag.infrastructure.pg.pg_rate_limiter import PgRateLimiter
from opensddrag.infrastructure.pg.pg_tool_registry import PgToolRegistry


def _settings(*, database_url: str, rate_limiter: str = "pg") -> SimpleNamespace:
    return SimpleNamespace(
        database_url=database_url,
        rate_limiter=rate_limiter,
        rate_limiter_quota=60,
        rate_limiter_window_seconds=60,
    )


# ─── Test 1: returns a UseCases instance ───────────────────────────────────


def test_build_use_cases_returns_use_cases() -> None:
    """`build_use_cases` returns a `UseCases` with both use cases built."""
    uc = build_use_cases(_settings(database_url="postgresql://x/y"))
    assert isinstance(uc, UseCases)
    assert isinstance(uc.execute_tool, ExecuteToolUseCase)
    assert isinstance(uc.list_tools, ListToolsUseCase)
    # Postgres mode selected the PG adapters.
    assert isinstance(uc.rate_limiter, PgRateLimiter)
    assert isinstance(uc.tool_registry, PgToolRegistry)


# ─── Test 2: in-memory adapters when DATABASE_URL is empty ─────────────────


def test_falls_back_to_in_memory_when_no_database_url() -> None:
    """An empty `database_url` selects the in-memory adapters."""
    uc = build_use_cases(_settings(database_url=""))
    assert isinstance(uc.rate_limiter, InMemoryRateLimiter)
    assert isinstance(uc.tool_registry, InMemoryToolRegistry)
    # The in-memory registry still exposes the full canonical tool set.
    assert len(uc.tool_registry.list()) == 22

    # RATE_LIMITER=memory also forces in-memory even with a database_url.
    uc_mem = build_use_cases(
        _settings(database_url="postgresql://x/y", rate_limiter="memory")
    )
    assert isinstance(uc_mem.rate_limiter, InMemoryRateLimiter)


# ─── Test 3: ports are wired through to the use cases ──────────────────────


def test_ports_are_wired() -> None:
    """The use cases share the exact adapter instances on `UseCases`."""
    uc = build_use_cases(_settings(database_url="postgresql://x/y"))

    # ExecuteToolUseCase holds the same registry exposed on UseCases.
    assert uc.execute_tool._tool_registry is uc.tool_registry
    # ListToolsUseCase shares the same registry too.
    assert uc.list_tools._tool_registry is uc.tool_registry
    # The rate limiter and logger are shared, not re-instantiated.
    assert uc.execute_tool._rate_limiter is uc.rate_limiter
    assert uc.execute_tool._logger is uc.logger
    assert uc.execute_tool._authenticator is uc.authenticator
