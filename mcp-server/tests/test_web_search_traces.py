"""Tests for GET /api/v1/search including execution traces (web-api-management REQ-007).

Service-level tests use the REAL SqlManagementService with repositories
patched (no DB).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from opensddrag.models.artifact import Artifact, ArtifactStatus, ArtifactType
from opensddrag.models.project import Project
from opensddrag.models.trace import ExecutionTrace


def _project() -> Project:
    now = datetime.now(tz=timezone.utc)
    return Project(
        id=uuid.uuid4(),
        slug="demo",
        name="Demo",
        description=None,
        metadata={},
        created_at=now,
        updated_at=now,
    )


def _artifact(project: Project) -> Artifact:
    now = datetime.now(tz=timezone.utc)
    return Artifact(
        id=uuid.uuid4(),
        project_id=project.id,
        name="harness-spec",
        type=ArtifactType.spec,
        status=ArtifactStatus.draft,
        content="harness " * 20,
        metadata={},
        created_at=now,
        updated_at=now,
    )


def _trace(project: Project) -> ExecutionTrace:
    return ExecutionTrace(
        id=uuid.uuid4(),
        project_id=project.id,
        session_id=None,
        action="search",
        artifact_id=None,
        query="harness",
        result_summary="found harness rules",
        metadata={},
        created_at=datetime.now(tz=timezone.utc),
    )


# ── Unit 1: mixed results (REQ-007) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_returns_artifacts_and_traces() -> None:
    from opensddrag.infrastructure import management_service as ms

    project = _project()
    artifact = _artifact(project)
    trace = _trace(project)

    async def fake_search(*_a, **_k):
        return [artifact]

    async def fake_projects():
        return [project]

    async def fake_recall(_pid, _vec, limit=5):
        return [trace]

    with patch.object(ms.repository, "search_semantic", fake_search), patch.object(
        ms.project_repository, "list_projects", fake_projects
    ), patch.object(ms.trace_repository, "recall", fake_recall):
        results = await ms.SqlManagementService().search("harness", limit=5)

    types = {r["type"] for r in results}
    assert "spec" in types
    assert "trace" in types
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    for r in results:
        assert set(r) == {"type", "title", "snippet", "project", "score", "slug"}


# ── Unit 2: trace present (REQ-007) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_includes_trace_when_matching() -> None:
    from opensddrag.infrastructure import management_service as ms

    project = _project()
    trace = _trace(project)

    async def fake_search(*_a, **_k):
        return []

    async def fake_projects():
        return [project]

    async def fake_recall(_pid, _vec, limit=5):
        return [trace]

    with patch.object(ms.repository, "search_semantic", fake_search), patch.object(
        ms.project_repository, "list_projects", fake_projects
    ), patch.object(ms.trace_repository, "recall", fake_recall):
        results = await ms.SqlManagementService().search("harness", limit=5)

    assert any(r["type"] == "trace" for r in results)