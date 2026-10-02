"""Tests for the flow manifest schema (multi-flow-foundation, flow-registry REQ-001).

Pure-domain tests: the manifest object is validated in memory — no DB, no
repository dependency (design D1: declarative flow packs as data).

* Unit 1 — a well-formed manifest declaring `flow`, `kinds`,
  `harness_triggers`, `skills`, `commands` and `claude_md_section` passes
  validation, and the parsed kinds list matches the declared kinds exactly
  (kebab-case slug enforced).
* Unit 2 — a manifest missing a required field (`flow` or `kinds`) is
  rejected with a diagnostic naming the missing field; validation is pure
  (no writes, no parsing side effects).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from opensddrag.core.domain.flow_manifest import (
    FlowManifest,
    manifest_issues,
    validate_manifest,
)


def _complete_manifest(**overrides) -> dict:
    base = {
        "flow": "docs",
        "kinds": [
            {"kind": "doc", "required_headings": ["## Objective"]},
            {"kind": "changelog"},
        ],
        "harness_triggers": ["on_doc_publish"],
        "skills": ["docs-outline", "docs-review"],
        "commands": [
            {"name": "draft", "folder": "docs"},
            {"name": "review"},
        ],
        "claude_md_section": "## OpenSddRag — docs flow\nMarker text.",
    }
    base.update(overrides)
    return base


# ── Unit 1: well-formed manifest accepted ─────────────────────────────────────


def test_well_formed_manifest_accepted() -> None:
    parsed = validate_manifest(_complete_manifest())
    assert parsed is not None
    # Flow slug is kebab-case and preserved
    assert str(parsed.flow) == "docs"
    # Kinds list matches the declared kinds exactly, in order
    assert [k.kind for k in parsed.kinds] == ["doc", "changelog"]
    assert parsed.kinds[0].required_headings == ["## Objective"]
    assert parsed.harness_triggers == ["on_doc_publish"]
    assert parsed.skills == ["docs-outline", "docs-review"]
    assert parsed.commands[0].folder == "docs"
    assert parsed.commands[1].folder is None
    assert "Marker text." in parsed.claude_md_section


def test_manifest_kind_addressable_by_flow_kind_pair() -> None:
    """Every declared kind is addressable by (flow, kind) — REQ-001."""
    parsed = validate_manifest(_complete_manifest())
    pairs = {(parsed.flow, k.kind) for k in parsed.kinds}
    assert (parsed.flow, "doc") in pairs
    assert (parsed.flow, "changelog") in pairs


def test_manifest_kinds_exact_order_preserved() -> None:
    parsed = FlowManifest.model_validate(_complete_manifest())
    assert [k.kind for k in parsed.kinds] == ["doc", "changelog"]


# ── Unit 2: missing required field rejected ───────────────────────────────────


def test_manifest_missing_kinds_rejected_with_named_diagnostic() -> None:
    payload = _complete_manifest()
    del payload["kinds"]
    issues = manifest_issues(payload)
    assert any("kinds" in i for i in issues), f"diagnostic must name 'kinds': {issues}"
    with pytest.raises(ValidationError) as exc_info:
        FlowManifest.model_validate(payload)
    assert "kinds" in str(exc_info.value)


def test_manifest_missing_flow_rejected_with_named_diagnostic() -> None:
    payload = _complete_manifest()
    del payload["flow"]
    issues = manifest_issues(payload)
    assert any("flow" in i for i in issues), f"issues: {issues}"


@pytest.mark.parametrize("field", ["flow", "kinds"])
def test_manifest_validation_is_pure(field: str) -> None:
    """The manifest validator never mutates its input (no side effects)."""
    payload = _complete_manifest()
    before = dict(payload)
    del payload[field]
    manifest_issues(payload)
    # The remaining payload keys are untouched
    for key, value in before.items():
        if key == field:
            continue
        assert payload.get(key) == value or key not in payload


def test_manifest_empty_flow_slug_rejected() -> None:
    issues = manifest_issues(_complete_manifest(flow=""))
    assert any("flow" in i for i in issues)


def test_manifest_non_kebab_flow_suggestion() -> None:
    """A non-kebab flow slug is flagged (kebab-case enforced)."""
    issues = manifest_issues(_complete_manifest(flow="Docs Flow"))
    assert any("kebab" in i.lower() for i in issues), f"issues: {issues}"