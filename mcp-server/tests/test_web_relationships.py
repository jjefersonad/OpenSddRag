"""Tests for GET /api/v1/artifacts/{id}/relationships (artifact-management REQ-002).

Service-level tests use the REAL SqlManagementService with repository
patched; router tests use a stub service.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from opensddrag.core.domain.errors import ResourceNotFoundError
from opensddrag.models.artifact import Artifact, ArtifactStatus, ArtifactType
from opensddrag.web.routes import build_routes


def _artifact() -> Artifact:
    return Artifact(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="task-1",
        type=ArtifactType.task,
        status=ArtifactStatus.active,
        content="x",
        metadata={},
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )


# ── Unit 1: linked artifact listed (REQ-002) ────────────────────────────────

@pytest.mark.asyncio
async def test_get_relationships_linked() -> None:
    from opensddrag.infrastructure import management_service as ms

    art = _artifact()

    async def fake_get(_aid):
        return art

    async def fake_rels(_aid):
        return [
            {
                "relationship_type": "implements",
                "id": uuid.uuid4(),
                "name": "some-spec",
                "type": "spec",
                "status": "draft",
                "project_id": art.project_id,
            }
        ]

    with patch.object(ms.repository, "get_artifact_by_id", fake_get), patch.object(
        ms.repository, "get_relationships", fake_rels
    ):
        rows = await ms.SqlManagementService().get_relationships(str(art.id))

    assert rows[0]["relationship_type"] == "implements"
    assert rows[0]["name"] == "some-spec"
    assert rows[0]["type"] == "spec"
    assert rows[0]["status"] == "draft"


# ── Unit 2: unknown id (REQ-002) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_relationships_unknown() -> None:
    from opensddrag.infrastructure import management_service as ms

    async def fake_get(_aid):
        return None

    with patch.object(ms.repository, "get_artifact_by_id", fake_get):
        with pytest.raises(ResourceNotFoundError):
            await ms.SqlManagementService().get_relationships(str(uuid.uuid4()))


class _StubService:
    def __init__(self, rows=None, error=None):
        self._rows = rows
        self._error = error

    async def get_relationships(self, artifact_id):
        if self._error:
            raise self._error
        return self._rows


class _FakeSettings:
    management_token = "t"
    web_origin = "http://localhost:3001"


def _client(service) -> TestClient:
    return TestClient(Starlette(routes=build_routes(service)))


def test_relationships_route_contract(monkeypatch) -> None:
    import opensddrag.web.deps as deps

    monkeypatch.setattr(deps, "settings", _FakeSettings())

    ok = _client(
        _StubService(rows=[{"relationship_type": "implements", "id": "1", "name": "s", "type": "spec", "status": "draft"}])
    ).get("/api/v1/artifacts/abc/relationships", headers={"Authorization": "Bearer t"})
    assert ok.status_code == 200
    assert ok.json()[0]["relationship_type"] == "implements"

    missing = _client(_StubService(error=ResourceNotFoundError("x"))).get(
        "/api/v1/artifacts/x/relationships", headers={"Authorization": "Bearer t"}
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"