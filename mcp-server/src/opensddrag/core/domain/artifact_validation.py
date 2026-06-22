"""Domain-level structural validation for SDD artifacts.

`validate` is a pure function — it checks content shape, not DB state.
It lives in `core/domain/` so both the infrastructure executor and any
future adapter can import it without creating an upward dependency.
"""

from __future__ import annotations


def validate(artifact_type: str, content: str) -> list[str]:
    """Return a list of structural issues with `content` for `artifact_type`.

    An empty list means no issues were found. Callers should treat a
    non-empty list as a validation failure (``{"valid": False, "issues": [...]}`).
    """
    issues: list[str] = []
    if len(content.strip()) < 10:
        issues.append("Content is too short (minimum 10 characters).")
    if artifact_type == "spec":
        if "Purpose" not in content:
            issues.append("Spec must have a 'Purpose' section.")
        if "Requirements" not in content:
            issues.append("Spec must have a 'Requirements' section.")
    if artifact_type == "task":
        if not content.strip():
            issues.append("Task content cannot be empty.")
        if "## Goal" not in content:
            issues.append(
                "Task must have a '## Goal' section describing what this task accomplishes."
            )
        if "## Acceptance Criteria" not in content:
            issues.append(
                "Task must have an '## Acceptance Criteria' section with verifiable criteria."
            )
    return issues


__all__ = ["validate"]
