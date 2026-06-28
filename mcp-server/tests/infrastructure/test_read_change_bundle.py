"""Tests for the `read_change_bundle` executor (reduce-token-consumption tier3-2).

Capability: `read-change-bundle`.
- REQ-001 — members resolved by `metadata.change_name` (NOT relationships);
  unrelated changes excluded; unknown change → error payload.
- REQ-002 — response shape `{proposal, design, specs, tasks, task_count}`;
  proposal/design carry full content (design `null` when absent); specs full;
  tasks are `{name, status}` only; `task_count == len(tasks)`.
- REQ-003 — no `etag`/version/lock field.

These tests are deterministic and DB-free: `repository.list_artifacts` is
monkeypatched to return a fixed in-memory artifact set, so no Postgres or
network is required.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from opensddrag.db import repository
from opensddrag.infrastructure.pg.tool_executors import read_change_bundle
from opensddrag.models.artifact import Artifact, ArtifactStatus, ArtifactType

_PROJECT_ID = uuid4()
_NOW = datetime(2026, 6, 28, 0, 0, 0, tzinfo=timezone.utc)


def _artifact(name: str, kind: ArtifactType, change: str, content: str = "x") -> Artifact:
    return Artifact(
        id=uuid4(),
        project_id=_PROJECT_ID,
        name=name,
        type=kind,
        status=ArtifactStatus.draft,
        content=content,
        metadata={"change_name": change},
        created_at=_NOW,
        updated_at=_NOW,
    )


def _foo_change() -> list[Artifact]:
    """A representative `foo` change plus an unrelated `bar` artifact."""
    return [
        _artifact("foo-proposal", ArtifactType.proposal, "foo", content="P" * 50),
        _artifact("foo-design", ArtifactType.design, "foo", content="D" * 80),
        _artifact("foo-a-spec", ArtifactType.spec, "foo", content="SPEC-A-FULL"),
        _artifact("foo-b-spec", ArtifactType.spec, "foo", content="SPEC-B-FULL"),
        *[
            _artifact(f"foo-task-{i}", ArtifactType.task, "foo", content="T" * 30)
            for i in range(6)
        ],
        # Unrelated change — must never leak into the foo bundle.
        _artifact("bar-proposal", ArtifactType.proposal, "bar"),
        _artifact("bar-task-1", ArtifactType.task, "bar"),
    ]


@pytest.fixture
def patched_repo(monkeypatch):
    """Patch `repository.list_artifacts` to return a configurable artifact set."""

    def _install(artifacts: list[Artifact]) -> None:
        async def _stub(project_id, type=None, status=None):  # noqa: A002
            return list(artifacts)

        monkeypatch.setattr(repository, "list_artifacts", _stub)

    return _install


async def _call(change_name: str):
    return await read_change_bundle(
        {"change_name": change_name},
        project_id=_PROJECT_ID,
        caller_id="test",
        conn=None,
    )


# ── REQ-001 — member resolution by change_name ───────────────────────────────


async def test_all_members_returned_and_other_change_excluded(patched_repo):
    patched_repo(_foo_change())

    bundle = await _call("foo")

    assert bundle["proposal"]["name"] == "foo-proposal"
    assert bundle["design"]["name"] == "foo-design"
    assert {s["name"] for s in bundle["specs"]} == {"foo-a-spec", "foo-b-spec"}
    task_names = {t["name"] for t in bundle["tasks"]}
    assert task_names == {f"foo-task-{i}" for i in range(6)}
    # No `bar`-tagged artifact appears anywhere in the foo bundle.
    all_names = (
        [bundle["proposal"]["name"], bundle["design"]["name"]]
        + [s["name"] for s in bundle["specs"]]
        + list(task_names)
    )
    assert not any(n.startswith("bar-") for n in all_names)


async def test_unknown_change_returns_error_payload(patched_repo):
    patched_repo(_foo_change())

    bundle = await _call("does-not-exist")

    assert bundle == {"error": "No artifacts found for change 'does-not-exist'."}


# ── REQ-002 — response shape ─────────────────────────────────────────────────


async def test_specs_full_tasks_summarized_and_task_count(patched_repo):
    patched_repo(_foo_change())

    bundle = await _call("foo")

    assert set(bundle.keys()) == {"proposal", "design", "specs", "tasks", "task_count"}
    # Specs keep their full content …
    spec_contents = {s["content"] for s in bundle["specs"]}
    assert spec_contents == {"SPEC-A-FULL", "SPEC-B-FULL"}
    # … while tasks are summarized to name+status only (no content).
    for task in bundle["tasks"]:
        assert set(task.keys()) == {"name", "status"}
    assert bundle["task_count"] == len(bundle["tasks"]) == 6


async def test_missing_design_is_null(patched_repo):
    members = [a for a in _foo_change() if a.type != ArtifactType.design]
    patched_repo(members)

    bundle = await _call("foo")

    assert bundle["design"] is None
    # The rest of the bundle is still returned.
    assert bundle["proposal"]["name"] == "foo-proposal"
    assert len(bundle["specs"]) == 2
    assert bundle["task_count"] == 6


# ── REQ-003 — no etag/version token ──────────────────────────────────────────


async def test_response_has_no_etag_or_version_field(patched_repo):
    patched_repo(_foo_change())

    bundle = await _call("foo")

    forbidden = {"etag", "version", "lock", "revision", "_etag"}
    assert forbidden.isdisjoint(bundle.keys())
