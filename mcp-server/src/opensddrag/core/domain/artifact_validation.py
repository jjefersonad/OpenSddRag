"""Domain-level structural validation for SDD artifacts.

`validate` is a pure function — it checks content shape, not DB state.
It lives in `core/domain/` so both the infrastructure executor and any
future adapter can import it without creating an upward dependency.

The task test-link check (REQ-005 MODIFIED of `embed-tdd-in-sdd-workflow`
→ `sdd-workflow-lifecycle`) deliberately takes pre-computed values from
the caller (``task_metadata`` and ``task_linked_test_count``) rather than
reaching out to the database itself. The function remains pure — its
inputs are plain data — but the caller is responsible for surfacing the
DB-backed bits, which keeps `core/domain/` free of repository
dependencies and makes the rule trivially testable in isolation.
"""

from __future__ import annotations

# Exact text mandated by REQ-005 (sdd-workflow-lifecycle MODIFIED) when a
# task fails the test-link requirement and is not exempt. Centralised so
# tests and the executor cannot drift apart from the spec.
_TASK_TEST_LINK_REQUIRED_MESSAGE = (
    'Task must link at least one test artifact '
    '(type="test", level="unit") via an implements relationship, '
    "or set metadata.test_exempt=true with a stated reason."
)

# Markers accepted as a stated reason in an exempt task's content.
# Conservative on purpose: prefer false negatives (forcing the author to
# add a more explicit `## Reason for exemption` heading) over false
# positives (silently accepting a content that happens to mention a
# reason-shaped phrase in passing).
_EXEMPT_REASON_MARKERS = (
    "## reason",
    "reason:",
    "rationale:",
    "no testable unit",
    "not testable",
    "exempt because",
)

# The only (flow, kind) pairs with a built-in Python validator. Their
# behaviour and exact messages are frozen by sdd-workflow-lifecycle
# REQ-004/REQ-005; every other pair uses declarative rules or the
# structural fallback (flow-registry REQ-003).
_BUILTIN_VALIDATORS: frozenset[tuple[str, str]] = frozenset(
    {("sdd", "spec"), ("sdd", "task")}
)


def validate(
    artifact_type: str,
    content: str,
    *,
    task_metadata: dict | None = None,
    task_linked_test_count: int = 0,
) -> list[str]:
    """Return a list of structural issues with `content` for `artifact_type`.

    An empty list means no issues were found. Callers should treat a
    non-empty list as a validation failure (``{"valid": False, "issues": [...]}`).

    ``task_metadata`` and ``task_linked_test_count`` are only consulted when
    ``artifact_type == "task"``; they are ignored for every other type.
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
        # REQ-005 (sdd-workflow-lifecycle MODIFIED): every task must either
        # link a unit-level test artifact, or carry an explicit
        # `metadata.test_exempt=true` with a stated reason in its content.
        issues.extend(
            _validate_task_test_link(
                content=content,
                task_metadata=task_metadata or {},
                task_linked_test_count=task_linked_test_count,
            )
        )
    return issues


def validate_registered(
    flow: str,
    kind: str,
    content: str,
    *,
    rules: dict | None = None,
    metadata: dict | None = None,
    name_is_unique: bool = True,
    task_metadata: dict | None = None,
    task_linked_test_count: int = 0,
) -> list[str]:
    """Select a validator by ``(flow, kind)`` — flow-registry REQ-003.

    Precedence:

    1. **Built-in Python validator** if one is registered for the pair.
       Only ``(sdd, spec)`` and ``(sdd, task)`` ship built-in; their
       messages are frozen and the declarative rules are ignored.
    2. **Declarative validation** when the ``artifact_kinds`` row carries
       ``required_headings`` / ``required_metadata_keys``: each listed
       heading must appear in ``content`` and each listed key must be a
       key of ``metadata``.
    3. **Structural fallback**: non-empty content (and a project-unique
       ``name`` when ``name_is_unique`` is False).

    Returns the issue list (empty = valid). Pure: no DB, no I/O — the
    caller surfaces the DB-backed ``rules`` / uniqueness facts.
    """
    rules = rules or {}

    # 1. Built-in SDD validators (frozen behaviour + exact messages).
    if (flow, kind) in _BUILTIN_VALIDATORS:
        return validate(
            kind,
            content,
            task_metadata=task_metadata,
            task_linked_test_count=task_linked_test_count,
        )

    # 2. Declarative rules from artifact_kinds.
    headings = rules.get("required_headings") or []
    metadata_keys = rules.get("required_metadata_keys") or []
    if headings or metadata_keys:
        issues: list[str] = []
        for heading in headings:
            if heading not in content:
                issues.append(f"Missing required heading: {heading}")
        meta = metadata or {}
        for key in metadata_keys:
            if key not in meta:
                issues.append(f"Missing required metadata key: {key}")
        return issues

    # 3. Structural fallback for kinds with no built-in and no rules.
    issues = []
    if not content.strip():
        issues.append("Content cannot be empty.")
    elif len(content.strip()) < 10:
        issues.append("Content is too short (minimum 10 characters).")
    if not name_is_unique:
        issues.append("Artifact name must be unique within the project.")
    return issues


def _validate_task_test_link(
    *,
    content: str,
    task_metadata: dict,
    task_linked_test_count: int,
) -> list[str]:
    """Apply the REQ-005 MODIFIED test-link / test-exemption check.

    Three valid outcomes (per the spec scenarios):

    1. Task is linked to ≥1 `test` artifact and is **not** exempt → valid.
    2. Task is exempt (``metadata.test_exempt is True``) **and** states a
       reason in its content → valid, even with zero linked tests.
    3. Otherwise → invalid with the mandated error message.

    An exempt task that omits its reason is rejected: the exemption
    flag is meaningless without justification, so falling back to the
    "must link a test" message keeps the failure mode uniform.
    """
    exempt = bool(task_metadata.get("test_exempt"))
    has_linked_test = task_linked_test_count >= 1

    if has_linked_test:
        # Linked: valid regardless of exemption flag — the link is the
        # strongest signal, no need to also police the exemption reason.
        return []

    if exempt:
        lowered = content.lower()
        if any(marker in lowered for marker in _EXEMPT_REASON_MARKERS):
            return []
        # Exempt but no reason stated — treat as "must link" since the
        # exemption is ungrounded and the agent should either re-justify
        # it or add the test artifact.
        return [_TASK_TEST_LINK_REQUIRED_MESSAGE]

    return [_TASK_TEST_LINK_REQUIRED_MESSAGE]


__all__ = ["validate"]
