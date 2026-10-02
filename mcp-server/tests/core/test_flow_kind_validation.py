"""Tests for the (flow, kind) validation registry (flow-registry REQ-003).

Precedence: built-in Python validator → declarative rules from
`artifact_kinds` → structural fallback. Result shape is unchanged:
`{"valid": bool, "issues": [str]}`.

* Unit 1 — built-in SDD validator precedence: `(sdd, spec)` missing
  `## Requirements` yields the exact prior message.
* Unit 2 — declarative validation from `artifact_kinds` rules:
  `required_headings`/`required_metadata_keys` produce named issues.
* Unit 3 — structural fallback for unknown kinds.

The pure selector is `validate_registered`; the executor-level wiring
through `validate_artifact` is covered by the integration class.
"""

from __future__ import annotations

import pytest

from opensddrag.core.domain.artifact_validation import validate_registered


# ── Unit 1: built-in SDD validator precedence ────────────────────────────────


def test_builtin_sdd_spec_missing_requirements_exact_message() -> None:
    issues = validate_registered(
        "sdd",
        "spec",
        "# foo Specification\n\n## Purpose\nSomething meaningful here.",
    )
    assert issues == ["Spec must have a 'Requirements' section."]


def test_builtin_sdd_spec_valid() -> None:
    issues = validate_registered(
        "sdd",
        "spec",
        "# foo Specification\n\n## Purpose\nSomething meaningful here."
        "\n\n## Requirements\n### Requirement: REQ-001 x\nbody",
    )
    assert issues == []


def test_builtin_sdd_task_keeps_shape_and_link_checks() -> None:
    content = "## Goal\nDo it well.\n\n## Acceptance Criteria\n- [ ] REQ-001 x"
    # no linked test, not exempt → link message
    issues = validate_registered("sdd", "task", content)
    assert any("test artifact" in i for i in issues)
    # linked test → valid
    issues = validate_registered(
        "sdd", "task", content, task_linked_test_count=1
    )
    assert issues == []


def test_builtin_precedence_beats_declarative_rules() -> None:
    """A (sdd, spec) with declarative rules present still uses the built-in."""
    issues = validate_registered(
        "sdd",
        "spec",
        "# foo\n\n## Purpose\nMeaningful body text here.",
        rules={"required_headings": ["## Nonexistent"]},
    )
    assert issues == ["Spec must have a 'Requirements' section."]
    assert not any("Nonexistent" in i for i in issues)


# ── Unit 2: declarative validation from artifact_kinds rules ──────────────────


def test_declarative_required_heading_missing() -> None:
    issues = validate_registered(
        "marketing",
        "brief",
        "A brief body without the required heading but long enough.",
        rules={"required_headings": ["## Objective"]},
    )
    assert issues == ["Missing required heading: ## Objective"]


def test_declarative_required_heading_present() -> None:
    issues = validate_registered(
        "marketing",
        "brief",
        "## Objective\nShip the campaign with a clear goal.",
        rules={"required_headings": ["## Objective"]},
    )
    assert issues == []


def test_declarative_required_metadata_key_missing() -> None:
    issues = validate_registered(
        "marketing",
        "brief",
        "## Objective\nShip the campaign with a clear goal.",
        rules={"required_metadata_keys": ["target_audience"]},
        metadata={"channel": "email"},
    )
    assert issues == ["Missing required metadata key: target_audience"]


def test_declarative_metadata_keys_all_present() -> None:
    issues = validate_registered(
        "marketing",
        "brief",
        "## Objective\nShip the campaign with a clear goal.",
        rules={"required_metadata_keys": ["target_audience"]},
        metadata={"target_audience": "smb"},
    )
    assert issues == []


# ── Unit 3: structural fallback for unknown kinds ─────────────────────────────


def test_fallback_valid_when_content_non_empty() -> None:
    issues = validate_registered(
        "docs",
        "doc-discovery",
        "A perfectly fine free-text artifact body.",
        rules={},
    )
    assert issues == []


def test_fallback_invalid_when_content_empty() -> None:
    issues = validate_registered("docs", "doc-discovery", "", rules={})
    assert issues, "empty content must fail the structural fallback"


def test_fallback_invalid_when_name_not_unique() -> None:
    issues = validate_registered(
        "docs",
        "doc-discovery",
        "A perfectly fine free-text artifact body.",
        rules={},
        name_is_unique=False,
    )
    assert any("unique" in i.lower() for i in issues)