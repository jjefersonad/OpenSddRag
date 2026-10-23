"""Live-change, phase and task-progress derivation (web-ui-prototype-fidelity).

Single source of truth for what a project's dashboard shows: which changes
are *live*, which lifecycle phase each one is in, and how many tasks are
done. Implements project-management REQ-005/006/007 and the derivations
behind web-api-management REQ-011/012.

Pure domain: stdlib only, no repository access. Callers map persisted
artifacts into `ChangeArtifact` and render the returned plain dicts.

Phase derivation is progress-based (REQ-005). The SDD commands only archive
tasks while a change is in flight — proposal, specs, design and tests stay
draft/active until the final archive — so a phase cannot be "done when its
artifacts are archived". Instead phases are *reached* by evidence, in
lifecycle order, using only the kinds the flow's manifest declares:

1. a phase declaring a kind no earlier phase declared is reached when an
   artifact of such a kind exists;
2. a phase whose kinds are all repeated and a subset of the previous
   phase's kinds is reached when at least one of its artifacts is done;
3. any other phase with only repeated kinds is reached when the previous
   phase's kinds have artifacts and every one is done;
4. a phase without kinds is never reached by evidence.

The furthest reached phase is active, earlier ones done, later ones pending.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

Lifecycle = Sequence[Mapping[str, Any]]

_MIN_DATE = datetime.min


@dataclass(frozen=True)
class ChangeArtifact:
    """The few artifact fields the derivations need (no content, no embedding).

    `done` carries the `metadata.done` flag only; an archived artifact is
    done too (`is_done`).
    """

    type: str
    status: str
    flow: str = "sdd"
    change_name: str | None = None
    is_delta: bool = True
    done: bool = False
    updated_at: datetime | None = None

    @property
    def is_done(self) -> bool:
        return self.done or self.status == "archived"


def is_synced_main_spec(artifact: ChangeArtifact) -> bool:
    """An active non-delta spec: the authoritative capability spec left by sync."""
    return artifact.type == "spec" and not artifact.is_delta and artifact.status == "active"


def _recency(artifacts: Sequence[ChangeArtifact]) -> datetime:
    stamps = [a.updated_at.replace(tzinfo=None) for a in artifacts if a.updated_at]
    return max(stamps, default=_MIN_DATE)


def _live_groups(
    artifacts: Sequence[ChangeArtifact],
) -> list[tuple[str | None, list[ChangeArtifact]]]:
    """Live `(change name | None, members)` groups, most recently updated first.

    Artifacts are grouped by `(flow, change_name)`; the group of artifacts
    without a change name is the implicit change of a flow that has no change
    concept (e.g. docs). A group is live when one member is non-archived;
    synced main specs never join a group (REQ-006), archived members stay as
    phase evidence.
    """
    groups: dict[tuple[str, str | None], list[ChangeArtifact]] = {}
    for artifact in artifacts:
        if is_synced_main_spec(artifact):
            continue
        groups.setdefault((artifact.flow, artifact.change_name), []).append(artifact)
    live = [
        (name, members)
        for (_flow, name), members in groups.items()
        if any(m.status != "archived" for m in members)
    ]
    live.sort(key=lambda item: _recency(item[1]), reverse=True)
    return live


def group_live_changes(artifacts: Sequence[ChangeArtifact]) -> dict[str, list[ChangeArtifact]]:
    """Named live changes keyed by name, most recently updated first (REQ-006)."""
    return {name: members for name, members in _live_groups(artifacts) if name}


def task_progress(artifacts: Sequence[ChangeArtifact]) -> dict[str, int]:
    """`{done, total}` over the tasks of `artifacts` (REQ-007)."""
    tasks = [a for a in artifacts if a.type == "task"]
    return {"done": sum(1 for t in tasks if t.is_done), "total": len(tasks)}


def _reached_index(lifecycle: Lifecycle, artifacts: Sequence[ChangeArtifact]) -> int:
    claimed: set[str] = set()
    previous: set[str] = set()
    reached = -1
    for index, phase in enumerate(lifecycle):
        kinds = set(phase.get("kinds") or [])
        fresh = kinds - claimed
        if not kinds:
            hit = False
        elif fresh:
            hit = any(a.type in fresh for a in artifacts)
        elif kinds <= previous:
            hit = any(a.type in kinds and a.is_done for a in artifacts)
        else:
            earlier = [a for a in artifacts if a.type in previous]
            hit = bool(earlier) and all(a.is_done for a in earlier)
        if hit:
            reached = index
        claimed |= kinds
        previous = kinds
    return reached


def derive_phases(
    lifecycle: Lifecycle | None, artifacts: Sequence[ChangeArtifact]
) -> list[dict[str, str]]:
    """Per-phase `{name, status}` of one change (REQ-005); `[]` without lifecycle."""
    if not lifecycle:
        return []
    members = [a for a in artifacts if not is_synced_main_spec(a)]
    reached = _reached_index(lifecycle, members)
    phases: list[dict[str, str]] = []
    for index, phase in enumerate(lifecycle):
        if reached < 0 or index > reached:
            status = "pending"
        elif index == reached:
            status = "active"
        else:
            status = "done"
        phases.append({"name": phase["name"], "status": status})
    return phases


def _active_name(phases: Sequence[Mapping[str, str]]) -> str | None:
    for phase in phases:
        if phase["status"] == "active":
            return phase["name"]
    return phases[0]["name"] if phases else None


def _pick_change(
    live: Sequence[tuple[str | None, list[ChangeArtifact]]], preferred_flow: str
) -> tuple[str | None, list[ChangeArtifact]] | None:
    """Most recent live group of `preferred_flow`, else of any flow."""
    for name, group in live:
        if group[0].flow == preferred_flow:
            return name, group
    return live[0] if live else None


def _summarize(
    lifecycle_by_flow: Mapping[str, Lifecycle | None],
    artifacts: Sequence[ChangeArtifact],
    preferred_flow: str,
) -> dict[str, Any]:
    live = _live_groups(artifacts)
    progress = {"done": 0, "total": 0}
    for _name, group in live:
        part = task_progress(group)
        progress["done"] += part["done"]
        progress["total"] += part["total"]

    picked = _pick_change(live, preferred_flow)
    if picked is not None:
        name, members = picked
        phases = derive_phases(lifecycle_by_flow.get(members[0].flow), members)
        phase = _active_name(phases)
    else:
        name = None
        lifecycle = lifecycle_by_flow.get(preferred_flow)
        if artifacts and lifecycle:
            phases = [{"name": p["name"], "status": "done"} for p in lifecycle]
            phase = phases[-1]["name"]
        else:
            phases, phase = [], None
    return {"change": name, "phase": phase, "phases": phases, "task_progress": progress}


def project_summary(
    lifecycle_by_flow: Mapping[str, Lifecycle | None],
    artifacts: Sequence[ChangeArtifact],
    default_flow: str,
) -> dict[str, Any]:
    """`{change, phase, phases, task_progress}` of a project (REQ-005, REQ-012).

    Stage and pipeline come from the most recently updated live change of
    the default flow (any flow when the default has none); progress sums
    every live change (REQ-007).
    """
    return _summarize(lifecycle_by_flow, artifacts, default_flow)


def flow_summaries(
    lifecycle_by_flow: Mapping[str, Lifecycle | None],
    artifacts: Sequence[ChangeArtifact],
) -> list[dict[str, Any]]:
    """Per-flow `{flow, phase, task_progress}` for the project detail (REQ-003)."""
    by_flow: dict[str, list[ChangeArtifact]] = {}
    for artifact in artifacts:
        by_flow.setdefault(artifact.flow, []).append(artifact)
    summaries: list[dict[str, Any]] = []
    for flow, members in by_flow.items():
        summary = _summarize(lifecycle_by_flow, members, flow)
        summaries.append(
            {"flow": flow, "phase": summary["phase"], "task_progress": summary["task_progress"]}
        )
    return summaries
