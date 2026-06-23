"""Domain constants for Harness rule validation.

These values mirror the DB CHECK constraints defined in migration 003.
They live in `core/domain/` so they can be imported by both the
infrastructure executor (`infrastructure/pg/tool_executors.py`) and any
future adapter without creating an upward dependency.
"""

from __future__ import annotations

VALID_RULE_TRIGGERS: tuple[str, ...] = (
    "always",
    "on_apply",
    "on_verify",
    "on_archive",
    "on_spec",
)

VALID_RULE_CATEGORIES: tuple[str, ...] = (
    "architecture",
    "naming",
    "forbidden",
    "doc-sync",
    "verification",
)

VALID_RULE_SEVERITIES: tuple[str, ...] = ("error", "warning", "info")

# Subset of VALID_RULE_TRIGGERS — 'always' is handled by get_working_context
# eager injection, not by the checklist tool.
VALID_HARNESS_CHECKLIST_TRIGGERS: tuple[str, ...] = (
    "on_apply",
    "on_verify",
    "on_archive",
    "on_spec",
)

__all__ = [
    "VALID_RULE_TRIGGERS",
    "VALID_RULE_CATEGORIES",
    "VALID_RULE_SEVERITIES",
    "VALID_HARNESS_CHECKLIST_TRIGGERS",
]
