"""Pure domain types for the OpenSddRag MCP server.

This package is the **innermost layer** of the architecture. It contains
only pure data types and pure functions — no I/O, no logging, no
configuration reads, no environment lookups. The import rule is enforced
both by the architecture tests (see task-architecture-tests-1) and by
the spec (mcp-domain-core-spec REQ-001 Scenario "Pure domain module is
importable without side effects").

Re-exports the public API of every submodule so callers can do:

    from opensddrag.core.domain import Tool, Permission, Response, ...

without caring about the internal sub-module layout.
"""

from opensddrag.core.domain.permission import (
    ALLOWED_KINDS,
    Allow,
    AuthorizationDecision,
    Deny,
    Permission,
    RequireConfirmation,
    is_allowed,
)
from opensddrag.core.domain.request import Request
from opensddrag.core.domain.response import Response
from opensddrag.core.domain.tool import Tool
from opensddrag.core.domain.validation import (
    Invalid,
    OK,
    ValidationError,
    ValidationResult,
    is_valid,
)

__all__ = [
    # permission
    "ALLOWED_KINDS",
    "Allow",
    "AuthorizationDecision",
    "Deny",
    "Permission",
    "RequireConfirmation",
    "is_allowed",
    # request
    "Request",
    # response
    "Response",
    # tool
    "Tool",
    # validation
    "Invalid",
    "OK",
    "ValidationError",
    "ValidationResult",
    "is_valid",
]
