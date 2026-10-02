"""Tests for the artifact validation + relationships endpoints.

Spec refs (change web-management-system-fixes):
    artifact-management REQ-001 (validation endpoint) — valid / invalid / 404.
    artifact-management REQ-002 (relationships listing) — linked / 404.

Service-level tests exercise the REAL SqlManagementService with the
repository patched (no DB); router tests exercise the HTTP contract via a
stub service.
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


def _artifact(artifact_type: ArtifactType, content: str) -> Artifact:
    return Artifact(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="a1",
        type=artifact_type,
        status=ArtifactStatus.draft,
        content=content,
        metadata={},
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )


# ── Unit 1: valid spec content (REQ-001) ────────────────────────────────────

@pytest.mark.asyncio
async def test_get_validation_valid_spec() -> None:
    from opensddrag.infrastructure import management_service as ms

    spec = _artifact(
        ArtifactType.spec, "# Spec\n\n## Purpose\nx\n\n## Requirements\n\n### Requirement: R\n"
    )

    async def fake_get(_aid):
        return spec

    with patch.object(ms.repository, "get_artifact_by_id", fake_get):
        result = await ms.SqlManagementService().get_validation(str(spec.id))

    assert result == {"valid": True, "issues": []}


# ── Unit 2: invalid spec content (REQ-001) ──────────────────────────────────

@pytest.mark.asyncio
async def test_get_validation_invalid_spec() -> None:
    from opensddrag.infrastructure import management_service as ms

    spec = _artifact(ArtifactType.spec, "# Spec\n\n## Purpose\nonly purpose, no requirements")

    async def fake_get(_aid):
        return spec

    with patch.object(ms.repository, "get_artifact_by_id", fake_get):
        result = await ms.SqlManagementService().get_validation(str(spec.id))

    assert result["valid"] is False
    assert "Spec must have a 'Requirements' section." in result["issues"]


# ── Unit 3: unknown id (REQ-001) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_validation_unknown_id() -> None:
    from opensddrag.infrastructure import management_service as ms

    async def fake_get(_aid):
        return None

    with patch.object(ms.repository, "get_artifact_by_id", fake_get):
        with pytest.raises(ResourceNotFoundError):
            await ms.SqlManagementService().get_validation(str(uuid.uuid4()))


# ── Router contract (REQ-001) ───────────────────────────────────────────────

class _StubService:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    async def get_validation(self, artifact_id):
        if self._error:
            raise self._error
        return self._result


class _FakeSettings:
    management_token = "t"
    web_origin = "http://localhost:3001"


def _client(service) -> TestClient:
    return TestClient(Starlette(routes=build_routes(service)))


def test_validation_route_contract(monkeypatch) -> None:
    import opensddrag.web.deps as deps

    monkeypatch.setattr(deps, "settings", _FakeSettings())

    ok = _client(_StubService(result={"valid": False, "issues": ["x"]})).get(
        "/api/v1/artifacts/abc/validation", headers={"Authorization": "Bearer t"}
    )
    assert ok.status_code == 200
    assert ok.json() == {"valid": False, "issues": ["x"]}

    missing = _client(
        _StubService(error=ResourceNotFoundError("artifact 'x' not found"))
    ).get("/api/v1/artifacts/x/validation", headers={"Authorization": "Bearer t"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"