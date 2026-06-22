"""Composition root — the single place that wires ports to adapters.

`build_use_cases(settings)` constructs every concrete adapter and
assembles the use cases (`ExecuteToolUseCase`, `ListToolsUseCase`)
behind their ports. It returns a frozen `UseCases` dataclass that the
MCP adapter (and any future REST/CLI adapter) consumes.

This is the **only** module in the project allowed to import from all
of `core/`, `infrastructure/`, and `db/` at once — it is the apex of
the dependency graph, so it cannot create a cycle. The architecture
test `tests/architecture/test_imports.py::test_infrastructure_only_imports_downward`
explicitly exempts this file from the "no `core.usecases` import" rule.

Adapter selection (criterion of `task-composition-1`):
    * Postgres adapters when `settings.database_url` is set **and**
      `settings.rate_limiter != "memory"`.
    * In-memory adapters otherwise (empty `DATABASE_URL`, or
      `RATE_LIMITER=memory`).

Tool executors: per the design's vertical-slice plan, the concrete
per-tool executor callables are extracted from the legacy `_dispatch`
body into `infrastructure/pg/tool_executors.py` by `task-adapter-1`
(Phase 4). To keep the composition root usable and testable *before*
that extraction, `build_use_cases` accepts an injectable
`tool_executors` mapping (empty by default). Once `task-adapter-1`
lands, it passes the populated mapping here — no change to the wiring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opensddrag.core.domain.tool import Tool
from opensddrag.core.ports.authentication import AuthenticationPort
from opensddrag.core.ports.executor import ToolExecutorPort
from opensddrag.core.ports.logger import LoggerPort
from opensddrag.core.ports.rate_limiter import RateLimiterPort
from opensddrag.core.ports.tool_registry import ToolRegistryPort
from opensddrag.core.usecases.execute_tool import ExecuteToolUseCase
from opensddrag.core.usecases.list_tools import ListToolsUseCase
from opensddrag.db.connection import get_conn
from opensddrag.infrastructure.auth.authorization_policy import (
    DefaultAuthorizationPolicy,
)
from opensddrag.infrastructure.auth.noop_authenticator import NoopAuthenticator
from opensddrag.infrastructure.memory.in_memory_rate_limiter import (
    InMemoryRateLimiter,
)
from opensddrag.infrastructure.memory.in_memory_tool_registry import (
    InMemoryToolRegistry,
)
from opensddrag.infrastructure.pg.pg_logger import PgLogger
from opensddrag.infrastructure.pg.pg_rate_limiter import PgRateLimiter
from opensddrag.infrastructure.pg.pg_tool_registry import PgToolRegistry
from opensddrag.infrastructure.validation.json_schema_validator import (
    JsonSchemaValidator,
)


@dataclass(frozen=True)
class UseCases:
    """The assembled use cases plus the long-lived adapters they share.

    Returned by `build_use_cases`. Frozen so the MCP adapter cannot
    accidentally re-wire a port at request time. The `tool_registry`,
    `authenticator`, `rate_limiter`, and `logger` are exposed (in
    addition to the use cases) so the adapter can build the `Caller`,
    surface health info, and reuse the same logger for transport-level
    events.
    """

    execute_tool: ExecuteToolUseCase
    list_tools: ListToolsUseCase
    tool_registry: ToolRegistryPort
    authenticator: AuthenticationPort
    rate_limiter: RateLimiterPort
    logger: LoggerPort


class _MappingToolExecutor:
    """`ToolExecutorPort` that dispatches by `tool.name` to a mapping.

    The mapping is `{name: ToolExecutorPort}`, populated by the
    composition root from `tool_executors`. When a tool has no wired
    executor (the default state before `task-adapter-1` lands), it
    raises `KeyError` — the use case catches it and returns
    `Response.error(code="INTERNAL", ...)`, so an un-wired tool fails
    loudly rather than silently returning `None`.
    """

    def __init__(self, executors: dict[str, ToolExecutorPort]) -> None:
        self._executors = executors

    async def execute(self, tool: Tool, parameters: dict[str, Any]) -> Any:
        executor = self._executors.get(tool.name)
        if executor is None:
            raise KeyError(
                f"no executor wired for tool {tool.name!r}; the composition "
                f"root was built without an entry for it (see task-adapter-1)"
            )
        return await executor.execute(tool, parameters)


def _use_postgres(settings: Any) -> bool:
    """Return True when the Postgres adapters should be selected.

    Postgres is used when a `database_url` is configured AND the
    `rate_limiter` setting is not explicitly `"memory"`. An empty
    `database_url` (tests, ephemeral runs) or `RATE_LIMITER=memory`
    selects the in-memory adapters.
    """
    return bool(getattr(settings, "database_url", "")) and (
        getattr(settings, "rate_limiter", "pg") != "memory"
    )


def build_use_cases(
    settings: Any,
    *,
    tool_executors: dict[str, ToolExecutorPort] | None = None,
) -> UseCases:
    """Wire all ports to concrete adapters and build the use cases.

    Args:
        settings: The application settings object (typically
            `opensddrag.config.settings`). Read for `database_url`,
            `rate_limiter`, `rate_limiter_quota`, and
            `rate_limiter_window_seconds`.
        tool_executors: Optional `{name: ToolExecutorPort}` mapping. The
            executors are extracted from the legacy dispatch in
            `task-adapter-1`; until then this defaults to an empty
            mapping and the composition root is still fully constructed
            and testable.

    Returns:
        A frozen `UseCases` with the use cases and shared adapters.
    """
    executors = dict(tool_executors or {})

    # Stateless adapters — identical in both modes.
    logger = PgLogger()
    authenticator = NoopAuthenticator()
    authorization_policy = DefaultAuthorizationPolicy()
    validator = JsonSchemaValidator()  # implements both validator ports
    tool_executor = _MappingToolExecutor(executors)

    quota = getattr(settings, "rate_limiter_quota", 60)
    window_seconds = getattr(settings, "rate_limiter_window_seconds", 60)

    if _use_postgres(settings):
        # Postgres mode. The tool registry's metadata is static, but we
        # hand it the same `get_conn` factory and executor mapping so a
        # future DB-hydrated registry is a drop-in.
        tool_registry: ToolRegistryPort = PgToolRegistry(
            get_conn, tool_executors=executors
        )
        rate_limiter: RateLimiterPort = PgRateLimiter(
            quota=quota,
            window_seconds=window_seconds,
            logger=logger,
        )
    else:
        # In-memory mode. Reuse the canonical static tool definitions
        # (sourced from `PgToolRegistry`, which performs no I/O to build
        # them) so the two registries expose the exact same tool set.
        static_tools = PgToolRegistry(get_conn, tool_executors=executors).list()
        tool_registry = InMemoryToolRegistry(static_tools)
        rate_limiter = InMemoryRateLimiter(
            quota=quota, window_seconds=window_seconds
        )

    execute_tool = ExecuteToolUseCase(
        tool_registry=tool_registry,
        authenticator=authenticator,
        rate_limiter=rate_limiter,
        input_validator=validator,
        authorization_policy=authorization_policy,
        tool_executor=tool_executor,
        output_validator=validator,
        logger=logger,
    )
    list_tools = ListToolsUseCase(
        tool_registry=tool_registry,
        authorization_policy=authorization_policy,
        logger=logger,
    )

    return UseCases(
        execute_tool=execute_tool,
        list_tools=list_tools,
        tool_registry=tool_registry,
        authenticator=authenticator,
        rate_limiter=rate_limiter,
        logger=logger,
    )


__all__ = ["UseCases", "build_use_cases"]
