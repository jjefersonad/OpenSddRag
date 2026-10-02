"""Domain-level errors — importable by use-case and infrastructure layers."""

from __future__ import annotations


class ProjectNotResolvableError(Exception):
    """Raised when no project can be resolved for a tool call.

    Tells the caller exactly what to do: pass ``project_slug`` in the
    tool call, or ensure the API key is bound to a project.
    """


# ── Management-service errors (web-management-system) ────────────────────────
#
# Raised by the `/api/v1` management service (infrastructure) and mapped to
# HTTP status codes + the shared error envelope by the REST delivery adapter
# (web/). Defined in `core.domain` so every layer may import them without a
# cycle (domain is the innermost layer).


class ManagementServiceError(Exception):
    """Base class for failures the management REST adapter maps to HTTP."""

    def __init__(self, message: str, details: list | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ResourceNotFoundError(ManagementServiceError):
    """A requested project/artifact/rule does not exist (→ HTTP 404)."""


class ResourceConflictError(ManagementServiceError):
    """A uniqueness constraint was violated, e.g. duplicate slug (→ HTTP 409)."""


class ManagementValidationError(ManagementServiceError):
    """A business-rule validation failed (→ HTTP 422)."""


__all__ = [
    "ProjectNotResolvableError",
    "ManagementServiceError",
    "ResourceNotFoundError",
    "ResourceConflictError",
    "ManagementValidationError",
]
