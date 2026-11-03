"""Unit tests for core/domain/change_progress (web-ui-prototype-fidelity).

Covers project-management REQ-005 (progress-based phase), REQ-006 (live
change), REQ-007 (task completion) and web-api-management REQ-011/012
derivations. Pure domain: no DB, no I/O.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from opensddrag.core.domain.change_progress import (
    ChangeArtifact,
    derive_phases,
    flow_summaries,
    group_live_changes,
    is_synced_main_spec,
    project_summary,
    task_progress,
)

SDD_LIFECYCLE = [
    {"name": "Propose", "kinds": ["proposal"]},
    {"name": "Spec", "kinds": ["spec", "test"]},
    {"name": "Design", "kinds": ["design"]},
    {"name": "Tasks", "kinds": ["task"]},
    {"name": "Apply", "kinds": ["task"]},
    {"name": "Verify", "kinds": ["test"]},
    {"name": "Sync", "kinds": []},
    {"name": "Archive", "kinds": []},
]

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


def art(
    type_: str,
    status: str = "draft",
    change: str | None = "chg",
    *,
    delta: bool = True,
    done: bool = False,
    flow: str = "sdd",
    age_days: int = 0,
) -> ChangeArtifact:
    return ChangeArtifact(
        type=type_,
        status=status,
        flow=flow,
        change_name=change,
        is_delta=delta,
        done=done,
        updated_at=T0 + timedelta(days=age_days),
    )


def statuses(phases: list[dict]) -> dict[str, str]:
    return {p["name"]: p["status"] for p in phases}


# ── unit-1: is_synced_main_spec / group_live_changes (REQ-006) ────────────


class TestLiveChanges:
    def test_synced_main_spec_is_active_non_delta_spec(self):
        assert is_synced_main_spec(art("spec", "active", delta=False))
        assert not is_synced_main_spec(art("spec", "draft", delta=False))
        assert not is_synced_main_spec(art("spec", "active", delta=True))
        assert not is_synced_main_spec(art("design", "active", delta=False))

    def test_archived_change_with_active_main_spec_is_not_live(self):
        arts = [
            art("proposal", "archived"),
            art("spec", "archived", delta=True),
            art("design", "archived"),
            art("task", "archived"),
            art("spec", "active", delta=False),
        ]
        assert group_live_changes(arts) == {}

    def test_open_delta_spec_keeps_change_live(self):
        arts = [art("proposal", "archived"), art("spec", "draft", delta=True)]
        assert list(group_live_changes(arts)) == ["chg"]

    def test_draft_main_spec_of_change_in_flight_is_live(self):
        arts = [art("proposal", "archived"), art("spec", "draft", delta=False)]
        live = group_live_changes(arts)
        assert list(live) == ["chg"]
        assert len(live["chg"]) == 2

    def test_only_draft_proposal_is_live(self):
        assert list(group_live_changes([art("proposal", "draft")])) == ["chg"]

    def test_live_group_keeps_archived_members_but_not_synced_main_specs(self):
        arts = [
            art("proposal", "archived"),
            art("task", "draft"),
            art("spec", "active", delta=False),
        ]
        members = group_live_changes(arts)["chg"]
        assert [m.type for m in members] == ["proposal", "task"]

    def test_artifacts_without_change_name_are_ignored(self):
        assert group_live_changes([art("proposal", "draft", change=None)]) == {}

    def test_live_changes_ordered_by_most_recent_first(self):
        arts = [
            art("proposal", "draft", change="old", age_days=1),
            art("proposal", "draft", change="new", age_days=5),
        ]
        assert list(group_live_changes(arts)) == ["new", "old"]


# ── unit-2: task_progress (REQ-007) ───────────────────────────────────────


class TestTaskProgress:
    def test_archived_tasks_count_as_done(self):
        tasks = [art("task", "archived"), art("task", "archived"), art("task", "draft")]
        assert task_progress(tasks) == {"done": 2, "total": 3}

    def test_metadata_done_counts(self):
        assert task_progress([art("task", "draft", done=True)]) == {"done": 1, "total": 1}

    def test_non_task_artifacts_are_ignored(self):
        assert task_progress([art("spec", "archived")]) == {"done": 0, "total": 0}

    def test_project_aggregate_sums_live_changes_only(self):
        arts = [art("task", "draft", change="live") for _ in range(3)]
        arts += [art("task", "archived", change=f"h{i}") for i in range(150)]
        arts += [art("spec", "active", change=f"h{i}", delta=False) for i in range(3)]
        summary = project_summary({"sdd": SDD_LIFECYCLE}, arts, "sdd")
        assert summary["task_progress"] == {"done": 0, "total": 3}


# ── unit-3: derive_phases (REQ-005, REQ-011) ──────────────────────────────


class TestDerivePhases:
    def test_planning_artifacts_draft_tasks_none_done(self):
        arts = [
            art("proposal"),
            art("spec"),
            art("design"),
            art("task"),
            art("task"),
        ]
        assert statuses(derive_phases(SDD_LIFECYCLE, arts)) == {
            "Propose": "done",
            "Spec": "done",
            "Design": "done",
            "Tasks": "active",
            "Apply": "pending",
            "Verify": "pending",
            "Sync": "pending",
            "Archive": "pending",
        }

    def test_apply_starts_when_a_task_is_done(self):
        arts = [art("proposal"), art("spec"), art("design")]
        arts += [art("task", "archived")] * 2 + [art("task")] * 3
        result = statuses(derive_phases(SDD_LIFECYCLE, arts))
        assert result["Tasks"] == "done"
        assert result["Apply"] == "active"
        assert result["Verify"] == "pending"

    def test_verify_when_every_task_is_done(self):
        arts = [art("proposal"), art("spec")]
        arts += [art("task", "archived"), art("task", "draft", done=True)]
        result = statuses(derive_phases(SDD_LIFECYCLE, arts))
        assert result["Apply"] == "done"
        assert result["Verify"] == "active"
        assert result["Sync"] == "pending"

    def test_design_phase_when_no_tasks(self):
        arts = [art("proposal"), art("spec"), art("design", "active")]
        result = statuses(derive_phases(SDD_LIFECYCLE, arts))
        assert result["Design"] == "active"
        assert result["Tasks"] == "pending"

    def test_only_proposal(self):
        result = statuses(derive_phases(SDD_LIFECYCLE, [art("proposal")]))
        assert result["Propose"] == "active"
        assert result["Spec"] == "pending"

    def test_synced_main_spec_is_ignored(self):
        arts = [art("proposal"), art("spec", "active", delta=False)]
        result = statuses(derive_phases(SDD_LIFECYCLE, arts))
        assert result["Propose"] == "active"
        assert result["Spec"] == "pending"

    def test_no_lifecycle_yields_no_phases(self):
        assert derive_phases(None, [art("proposal")]) == []
        assert derive_phases([], [art("proposal")]) == []

    def test_no_evidence_means_everything_pending(self):
        result = statuses(derive_phases(SDD_LIFECYCLE, []))
        assert set(result.values()) == {"pending"}

    def test_phases_without_kinds_are_never_reached(self):
        arts = [art("proposal"), art("spec"), art("design")]
        arts += [art("task", "archived")]
        result = statuses(derive_phases(SDD_LIFECYCLE, arts))
        assert result["Sync"] == "pending"
        assert result["Archive"] == "pending"

    def test_generic_lifecycle_without_sdd_names(self):
        lifecycle = [
            {"name": "Draft", "kinds": ["note"]},
            {"name": "Review", "kinds": ["review"]},
        ]
        arts = [art("note"), art("review")]
        assert statuses(derive_phases(lifecycle, arts)) == {
            "Draft": "done",
            "Review": "active",
        }


# ── unit-4: project_summary / flow_summaries (REQ-005, REQ-012) ───────────


class TestProjectSummary:
    def test_phase_follows_most_recent_live_change(self):
        arts = [
            art("proposal", "archived", change="old", age_days=1),
            art("task", "archived", change="old", age_days=1),
            art("proposal", "draft", change="new", age_days=9),
        ]
        summary = project_summary({"sdd": SDD_LIFECYCLE}, arts, "sdd")
        assert summary["change"] == "new"
        assert summary["phase"] == "Propose"
        assert statuses(summary["phases"])["Propose"] == "active"

    def test_no_live_change_yields_last_phase(self):
        arts = [art("proposal", "archived"), art("task", "archived")]
        summary = project_summary({"sdd": SDD_LIFECYCLE}, arts, "sdd")
        assert summary["change"] is None
        assert summary["phase"] == "Archive"
        assert {p["status"] for p in summary["phases"]} == {"done"}

    def test_flow_without_lifecycle(self):
        summary = project_summary({"sdd": None}, [art("proposal")], "sdd")
        assert summary["phase"] is None
        assert summary["phases"] == []
        assert summary["change"] == "chg"

    def test_project_without_artifacts(self):
        summary = project_summary({"sdd": SDD_LIFECYCLE}, [], "sdd")
        assert summary == {
            "change": None,
            "phase": None,
            "phases": [],
            "task_progress": {"done": 0, "total": 0},
        }

    def test_summary_carries_progress_of_live_changes(self):
        arts = [
            art("proposal"),
            art("spec"),
            art("design"),
            art("task", "archived"),
            art("task", "archived"),
            art("task", "archived"),
            art("task"),
            art("task"),
        ]
        summary = project_summary({"sdd": SDD_LIFECYCLE}, arts, "sdd")
        assert summary["phase"] == "Apply"
        assert summary["task_progress"] == {"done": 3, "total": 5}

    def test_default_flow_preferred_then_fallback_to_any(self):
        arts = [
            art("proposal", change="a", flow="sdd", age_days=1),
            art("note", change="b", flow="docs", age_days=9),
        ]
        lifecycles = {"sdd": SDD_LIFECYCLE, "docs": [{"name": "Write", "kinds": ["note"]}]}
        assert project_summary(lifecycles, arts, "sdd")["change"] == "a"
        assert project_summary(lifecycles, arts, "other")["change"] == "b"

    def test_flow_summaries_per_flow(self):
        arts = [
            art("proposal", change="a", flow="sdd"),
            art("task", "archived", change="a", flow="sdd"),
            art("task", "draft", change="a", flow="sdd"),
            art("note", change="b", flow="docs"),
        ]
        lifecycles = {"sdd": SDD_LIFECYCLE, "docs": None}
        by_flow = {s["flow"]: s for s in flow_summaries(lifecycles, arts)}
        assert by_flow["sdd"]["phase"] == "Apply"
        assert by_flow["sdd"]["task_progress"] == {"done": 1, "total": 2}
        assert by_flow["docs"]["phase"] is None
        assert by_flow["docs"]["task_progress"] == {"done": 0, "total": 0}


class TestUnnamedChanges:
    """Flows without a change concept (e.g. docs) still get a stage."""

    def test_unnamed_artifacts_form_one_implicit_group_per_flow(self):
        lifecycle = {"docs": [{"name": "Objective", "kinds": ["doc"]}, {"name": "Publication", "kinds": ["changelog"]}]}
        arts = [art("doc", change=None, flow="docs")]
        summary = project_summary(lifecycle, arts, "docs")
        assert summary["change"] is None
        assert summary["phase"] == "Objective"
        assert statuses(summary["phases"]) == {"Objective": "active", "Publication": "pending"}

    def test_unnamed_group_counts_for_progress(self):
        arts = [art("task", "archived", change=None), art("task", change=None)]
        summary = project_summary({"sdd": SDD_LIFECYCLE}, arts, "sdd")
        assert summary["task_progress"] == {"done": 1, "total": 2}

    def test_named_group_listing_still_ignores_unnamed(self):
        assert group_live_changes([art("doc", change=None, flow="docs")]) == {}


@pytest.mark.parametrize("lifecycle", [None, []])
def test_summary_never_errors_without_lifecycle(lifecycle):
    summary = project_summary({"sdd": lifecycle}, [art("task")], "sdd")
    assert summary["phase"] is None
