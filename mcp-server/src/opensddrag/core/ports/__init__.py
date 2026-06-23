"""Dependency-inversion ports for the OpenSddRag MCP server use cases.

This package is the seam between the **pure use cases**
(`core/usecases/`) and the **concrete adapters** in
`infrastructure/`. It contains only `typing.Protocol` definitions — no
implementations. Use cases depend on these ports; the composition root
in `infrastructure/composition.py` binds them to concrete adapters.

Import rule (enforced by `tests/architecture/test_imports.py`, see
`task-architecture-tests-1`): this package MUST NOT import from
`mcp/`, `db/`, `embedding/`, `cli/`, `config/`, `models/`, or
`infrastructure/`. It MAY import from `typing`, `dataclasses`, and
`core.domain` (for the `Permission` enum, the `Tool` value object, and
the validation result types).

Re-exports the public API of every submodule so callers can do:

    from opensddrag.core.ports import (
        AuthenticationPort, Caller, ToolRegistryPort, ...
    )
"""

from opensddrag.core.ports.authentication import AuthenticationPort, Caller
from opensddrag.core.ports.authorization import AuthorizationPolicyPort
from opensddrag.core.ports.executor import ToolExecutorPort
from opensddrag.core.ports.logger import LoggerPort
from opensddrag.core.ports.rate_limiter import RateLimiterPort
from opensddrag.core.ports.tool_registry import ToolRegistryPort
from opensddrag.core.ports.validator import (
    InputValidatorPort,
    OutputValidatorPort,
)

__all__ = [
    # authentication
    "AuthenticationPort",
    "Caller",
    # authorization
    "AuthorizationPolicyPort",
    # executor
    "ToolExecutorPort",
    # logger
    "LoggerPort",
    # rate_limiter
    "RateLimiterPort",
    # tool_registry
    "ToolRegistryPort",
    # validator
    "InputValidatorPort",
    "OutputValidatorPort",
]
