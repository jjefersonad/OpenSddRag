"""Domain-level errors — importable by use-case and infrastructure layers."""

from __future__ import annotations


class ProjectNotResolvableError(Exception):
    """Raised when no project can be resolved for a tool call.

    Tells the caller exactly what to do: pass ``project_slug`` in the
    tool call, or ensure the API key is bound to a project.
    """


__all__ = ["ProjectNotResolvableError"]
