"""Flow manifest schema — pure-domain validation (multi-flow-foundation).

A flow manifest describes one workflow ("flow") as data: its artifact kinds
with optional declarative validation rules, its optional ordered lifecycle
phases, the harness triggers it uses, its skills and slash commands, and the
`CLAUDE.md` section it installs.
`flow-registry` REQ-001 defines the schema; this module is its single
authoritative parser/validator.

Pure domain: no repository access, no I/O. `validate_manifest` returns a
parsed `FlowManifest` or raises `ManifestValidationError` (a Pydantic
`ValueError` subclass carrying field-named diagnostics);
`manifest_issues` returns a list of human-readable diagnostics (empty
when valid) so CLI and tool layers can surface failures without
exception handling.

Kebab-case enforcement applies to the flow slug; kinds and command names
must be non-empty, file-safe strings.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, ValidationError, field_validator

_KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


class ManifestKind(BaseModel):
    """One artifact kind declared by a flow, with optional declarative rules."""

    kind: str
    required_headings: list[str] = Field(default_factory=list)
    required_metadata_keys: list[str] = Field(default_factory=list)


class ManifestPhase(BaseModel):
    """One lifecycle phase declared by a flow (web-ui-design-alignment REQ-006).

    A phase groups zero or more declared kinds in execution order — e.g. the
    sdd flow's `Propose` phase carries `proposal`, while closing phases
    (`Sync`, `Archive`) carry none. Pure data: validation of kind references
    and name uniqueness happens in `manifest_issues`.
    """

    name: str
    kinds: list[str] = Field(default_factory=list)


class ManifestCommand(BaseModel):
    """One slash command contributed by the flow."""

    name: str
    folder: str | None = None


class FlowManifest(BaseModel):
    """The complete manifest shape of `flow-registry` REQ-001.

    All six top-level fields are required; a manifest missing `flow` or
    `kinds` is rejected with a diagnostic naming the missing field.
    """

    flow: str
    kinds: list[ManifestKind]
    harness_triggers: list[str] = Field(default_factory=list)
    lifecycle: list[ManifestPhase] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    commands: list[ManifestCommand] = Field(default_factory=list)
    claude_md_section: str

    @field_validator("flow")
    @classmethod
    def _flow_is_kebab(cls, value: str) -> str:
        if not _KEBAB_RE.fullmatch(value):
            raise ValueError(
                f"Flow slug must be kebab-case (lowercase letters/digits "
                f"separated by single hyphens), got: {value!r}"
            )
        return value

    @field_validator("kinds")
    @classmethod
    def _kinds_are_declared(cls, kinds: list["ManifestKind"]) -> list["ManifestKind"]:
        if not kinds:
            raise ValueError("Manifest must declare at least one kind")
        return kinds


def manifest_issues(payload: dict) -> list[str]:
    """Return diagnostics for a manifest payload (empty list = valid).

    Pure function — never mutates `payload`, never touches storage.
    Field names appear verbatim in the issue text so callers can render
    the exact missing field (flow-registry REQ-001 abort diagnostic).
    """
    issues: list[str] = []

    if not isinstance(payload, dict):
        return [f"Manifest must be an object (got {type(payload).__name__})."]

    flow_value = payload.get("flow")
    if flow_value is None or not str(flow_value).strip():
        issues.append("Manifest is missing required field: flow")
    kinds_value = payload.get("kinds")
    if not isinstance(kinds_value, list) or not kinds_value:
        issues.append("Manifest is missing required field: kinds")

    if flow_value is not None and not _KEBAB_RE.fullmatch(str(flow_value)):
        issues.append(
            f"Flow slug must be kebab-case (lowercase letters/digits separated "
            f"by single hyphens), got: {flow_value!r}"
        )

    if isinstance(kinds_value, list):
        for i, kind in enumerate(kinds_value):
            if not isinstance(kind, dict) or not str(kind.get("kind") or "").strip():
                issues.append(f"kinds[{i}] must declare a non-empty 'kind'")
            elif not _SAFE_NAME_RE.fullmatch(str(kind["kind"])):
                issues.append(
                    f"kinds[{i}].kind must be alphanumeric/kebab-style, "
                    f"got: {kind.get('kind')!r}"
                )

    for i, cmd in enumerate(payload.get("commands", []) or []):
        if not isinstance(cmd, dict) or not _SAFE_NAME_RE.fullmatch(
            str(cmd.get("name") or "")
        ):
            issues.append(f"commands[{i}] must declare a non-empty 'name'")

    lifecycle = payload.get("lifecycle")
    if lifecycle is not None:
        declared = {str(k["kind"]) for k in kinds_value or [] if isinstance(k, dict)}
        names: list[str] = []
        if not isinstance(lifecycle, list) or not lifecycle:
            issues.append("lifecycle, when present, must be a non-empty list of phases")
        else:
            for i, phase in enumerate(lifecycle):
                if not isinstance(phase, dict) or not str(phase.get("name") or "").strip():
                    issues.append(f"lifecycle[{i}] must declare a non-empty 'name'")
                    continue
                phase_name = str(phase["name"])
                if phase_name in names:
                    issues.append(f"lifecycle[{i}] duplicates phase name {phase_name!r}")
                names.append(phase_name)
                phase_kinds = phase.get("kinds")
                if not isinstance(phase_kinds, list):
                    issues.append(
                        f"lifecycle[{i}] 'kinds' must be a list (closing phases may declare an empty list)"
                    )
                    continue
                if not phase_kinds:
                    # closing phases (e.g. Sync/Archive) may carry no kinds
                    continue
                for kind in phase_kinds:
                    if kind not in declared:
                        issues.append(
                            f"lifecycle[{i}] ({phase_name!r}) references kind "
                            f"{kind!r} which is not declared in kinds"
                        )

    if not str(payload.get("claude_md_section") or "").strip():
        issues.append("Manifest is missing required field: claude_md_section")

    return issues


def validate_manifest(payload: dict) -> FlowManifest:
    """Parse and validate a manifest payload.

    Runs the structural diagnostics first so a missing required field
    fails with a message naming that field, then delegates to the
    Pydantic model for shape/typing. Raises `ManifestValidationError`
    or ValidationError on any problem; returns the parsed manifest on
    success.
    """
    issues = manifest_issues(payload)
    if issues:
        raise ManifestValidationError(issues)
    return FlowManifest.model_validate(payload)


class ManifestValidationError(ValueError):
    """Field-named manifest failure (flow-registry REQ-001 abort).

    Subclasses ValueError so generic `except ValueError` call sites keep
    working; carries `issues` (the field-named diagnostics) for rendering.
    """

    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("Manifest is invalid: " + "; ".join(issues))