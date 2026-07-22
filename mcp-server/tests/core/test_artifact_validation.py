"""Unit tests for the pure `validate()` function in `artifact_validation`.

These tests cover the three scenarios of REQ-005 (sdd-workflow-lifecycle
MODIFIED) introduced by the `embed-tdd-in-sdd-workflow` change:

  * valid task with linked unit test
  * invalid task — no link and not exempt
  * valid exempt task (with stated reason)

plus the explicit error-message text and the regression that the
original `## Goal` / `## Acceptance Criteria` shape checks still apply.

The tests are pure: no PostgreSQL, no embedding model, no I/O. The
`task_linked_test_count` value is supplied directly by the caller, which
is exactly how the `validate_artifact` executor feeds the function once
it has queried the database.
"""

from __future__ import annotations

import pytest

from opensddrag.core.domain.artifact_validation import validate


# Spec-mandated error text — see REQ-005 (sdd-workflow-lifecycle MODIFIED).
EXPECTED_MISSING_LINK_MESSAGE = (
    'Task must link at least one test artifact '
    '(type="test", level="unit") via an implements relationship, '
    "or set metadata.test_exempt=true with a stated reason."
)


def _valid_task_content(extra: str = "") -> str:
    """A minimal task body that satisfies the original shape checks."""
    return (
        "## Goal\n"
        "Implement the thing.\n\n"
        "## Acceptance Criteria\n"
        "- [ ] REQ-001: it works.\n"
        f"\n{extra}"
    )


# ─── Shape checks (regression: original REQ-005) ───────────────────────────


class TestTaskShapeRegression:
    def test_task_missing_goal_is_rejected(self) -> None:
        issues = validate(
            "task",
            "## Acceptance Criteria\n- [ ] something",
        )
        assert any("## Goal" in msg for msg in issues)

    def test_task_missing_acceptance_criteria_is_rejected(self) -> None:
        issues = validate(
            "task",
            "## Goal\nDo the thing.",
        )
        assert any("## Acceptance Criteria" in msg for msg in issues)

    def test_task_with_shape_and_link_passes(self) -> None:
        issues = validate(
            "task",
            _valid_task_content(),
            task_metadata={},
            task_linked_test_count=1,
        )
        assert issues == []


# ─── REQ-005 MODIFIED: linked test artifact ────────────────────────────────


class TestTaskLinkedTest:
    def test_linked_task_with_no_exempt_passes(self) -> None:
        # Standard case: the task has at least one linked test, no
        # exemption declared, and the original shape sections are present.
        issues = validate(
            "task",
            _valid_task_content(),
            task_metadata={},
            task_linked_test_count=1,
        )
        assert issues == []

    def test_linked_task_with_exempt_flag_still_passes(self) -> None:
        # Linking is the strongest signal — even an exempt task with
        # a linked test passes without the agent having to also state
        # a reason. The exemption flag is moot.
        issues = validate(
            "task",
            _valid_task_content(),
            task_metadata={"test_exempt": True},
            task_linked_test_count=1,
        )
        assert issues == []

    def test_linked_task_with_multiple_tests_passes(self) -> None:
        # Sanity: more than one linked test is still fine.
        issues = validate(
            "task",
            _valid_task_content(),
            task_metadata={},
            task_linked_test_count=3,
        )
        assert issues == []


# ─── REQ-005 MODIFIED: missing link, not exempt ────────────────────────────


class TestTaskMissingLinkNotExempt:
    def test_missing_link_reports_spec_message(self) -> None:
        issues = validate(
            "task",
            _valid_task_content(),
            task_metadata={},
            task_linked_test_count=0,
        )
        assert issues == [EXPECTED_MISSING_LINK_MESSAGE]

    def test_missing_link_reports_message_even_with_other_metadata(self) -> None:
        # Other metadata keys must not be confused with the exemption flag.
        issues = validate(
            "task",
            _valid_task_content(),
            task_metadata={"group": "skills", "order": 4},
            task_linked_test_count=0,
        )
        assert issues == [EXPECTED_MISSING_LINK_MESSAGE]

    def test_missing_link_reports_message_when_exempt_flag_is_false(self) -> None:
        # Explicitly false should be treated as not exempt.
        issues = validate(
            "task",
            _valid_task_content(),
            task_metadata={"test_exempt": False},
            task_linked_test_count=0,
        )
        assert issues == [EXPECTED_MISSING_LINK_MESSAGE]

    def test_missing_link_reports_message_when_exempt_flag_is_truthy_non_bool(
        self,
    ) -> None:
        # The exemption path checks for *truthy* values; an empty dict is
        # falsy and must NOT count as an exemption, so the missing-link
        # message applies.
        issues = validate(
            "task",
            _valid_task_content(),
            task_metadata={"test_exempt": {}},
            task_linked_test_count=0,
        )
        assert issues == [EXPECTED_MISSING_LINK_MESSAGE]


# ─── REQ-005 MODIFIED: exempt with stated reason ──────────────────────────


class TestTaskExemptWithReason:
    @pytest.mark.parametrize(
        "marker",
        [
            "## Reason\nNo testable unit applies here.",
            "Reason: the work is a docs edit only.",
            "Rationale: SQL migration without runtime behavior.",
            "There is no testable unit to cover here.",
            "The behaviour is not testable in isolation.",
            "Exempt because this task only updates metadata.",
        ],
    )
    def test_exempt_with_marker_passes(self, marker: str) -> None:
        issues = validate(
            "task",
            _valid_task_content(extra=marker),
            task_metadata={"test_exempt": True},
            task_linked_test_count=0,
        )
        assert issues == []

    def test_exempt_without_reason_is_rejected(self) -> None:
        # Exemption flag is set but no reason is declared in the content —
        # the exemption is ungrounded, so the same missing-link message
        # applies.
        issues = validate(
            "task",
            _valid_task_content(),
            task_metadata={"test_exempt": True},
            task_linked_test_count=0,
        )
        assert issues == [EXPECTED_MISSING_LINK_MESSAGE]

    def test_exempt_with_reason_marker_is_case_insensitive(self) -> None:
        issues = validate(
            "task",
            _valid_task_content(extra="REASON: just a docs bump."),
            task_metadata={"test_exempt": True},
            task_linked_test_count=0,
        )
        assert issues == []


# ─── Non-task types ignore the new parameters ─────────────────────────────


class TestNonTaskTypesIgnoreNewParams:
    def test_spec_validation_ignores_task_metadata(self) -> None:
        # `task_metadata` and `task_linked_test_count` are only consulted
        # for `task`; for `spec` the old shape-only behaviour must hold.
        spec_content = (
            "## Purpose\nDo X.\n\n## Requirements\n\n### Requirement: REQ-001"
        )
        issues = validate(
            "spec",
            spec_content,
            task_metadata={"test_exempt": True},
            task_linked_test_count=0,
        )
        assert issues == []

    def test_proposal_validation_ignores_task_metadata(self) -> None:
        # Same for `proposal` — the new task-only parameters must not
        # cause a proposal to be rejected.
        issues = validate(
            "proposal",
            "## Why\nBecause.\n\n## What\nDo the thing.",
            task_metadata={"test_exempt": True},
            task_linked_test_count=0,
        )
        assert issues == []
