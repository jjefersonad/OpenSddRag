"""Read-router tests for the /api/v1 management REST adapter.

Spec refs:
    - project-management REQ-001/002/003 (list/create/detail-summary)
    - artifact-management REQ-001/002 (list by type, single read)
    - harness-rules-management REQ-001 (default listing excludes disabled)
    - web-api-management REQ-005 (search shape + missing q → 422)

The routers depend on `ManagementServiceProtocol`; these tests inject a
deterministic stub (per backend-architecture.md: delivery adapters are
exercised through their public HTTP API, with stubs preferred over
framework-heavy mocks).
"""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from opensddrag.core.domain.errors import (
    ResourceConflictError,
    ResourceNotFoundError,
)
from opensddrag.web.routes import build_routes

TOKEN = "test-token"


class FakeSettings:
    management_token = TOKEN
    web_origin = "http://localhost:3001"


class StubService:
    """Deterministic in-memory stub of ManagementServiceProtocol."""

    def __init__(
        self,
        *,
        projects=None,
        conflict_slug=None,
        artifacts_by_slug=None,
        artifact_by_id=None,
        rules_by_slug=None,
        traces_by_slug=None,
        search_results=None,
    ):
        self.projects = projects if projects is not None else []
        self.summary_by_slug = {}
        self.conflict_slug = conflict_slug
        self.artifacts_by_slug = artifacts_by_slug or {}
        self.artifact_by_id = artifact_by_id or {}
        self.rules_by_slug = rules_by_slug or {}
        self.traces_by_slug = traces_by_slug or {}
        self.search_results = search_results or []

    async def list_projects(self):
        return list(self.projects)

    async def create_project(self, name, slug, description=""):
        if slug == self.conflict_slug:
            raise ResourceConflictError(f"project slug {slug!r} already exists")
        created = {
            "id": "new-id",
            "name": name,
            "slug": slug,
            "description": description,
            "created_at": "2026-01-01T00:00:00Z",
        }
        self.projects.append(created)
        return created

    async def get_project(self, slug):
        for p in self.projects:
            if p["slug"] == slug:
                return {**p, "summary": self.summary_by_slug.get(slug, {})}
        raise ResourceNotFoundError(f"project {slug!r} not found")

    async def list_artifacts(self, slug, type_filter=None):
        if slug not in self.artifacts_by_slug:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        items = list(self.artifacts_by_slug[slug])
        if type_filter:
            items = [a for a in items if a["type"] == type_filter]
        return items

    async def get_artifact(self, artifact_id):
        if artifact_id not in self.artifact_by_id:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")
        return self.artifact_by_id[artifact_id]

    async def list_rules(self, slug, enabled_all=False):
        if slug not in self.rules_by_slug:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        rules = list(self.rules_by_slug[slug])
        if not enabled_all:
            rules = [r for r in rules if r["enabled"]]
        return rules

    async def list_traces(self, slug, limit=20):
        if slug not in self.traces_by_slug:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        return list(self.traces_by_slug[slug])[:limit]

    async def search(self, query, limit=5):
        return list(self.search_results)[:limit]


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    import opensddrag.web.deps as deps

    monkeypatch.setattr(deps, "settings", FakeSettings())


def _client(service) -> TestClient:
    return TestClient(Starlette(routes=build_routes(service)))


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


# ── Unit 1: projects CRUD endpoints (project-management REQ-001/002/003) ─────


def test_list_projects_returns_array() -> None:
    svc = StubService(projects=[{"id": "1", "name": "Demo", "slug": "demo", "description": "d", "created_at": "x"}])
    resp = _client(svc).get("/api/v1/projects", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == [{"id": "1", "name": "Demo", "slug": "demo", "description": "d", "created_at": "x"}]


def test_create_project_success_and_duplicate_and_invalid_slug() -> None:
    svc = StubService(conflict_slug="taken")
    client = _client(svc)

    ok = client.post("/api/v1/projects", json={"name": "Demo", "slug": "demo", "description": "d"}, headers=_auth())
    assert ok.status_code == 201
    assert ok.json()["slug"] == "demo"

    dup = client.post("/api/v1/projects", json={"name": "Taken", "slug": "taken"}, headers=_auth())
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "CONFLICT"

    bad = client.post("/api/v1/projects", json={"name": "Bad", "slug": "My Project!"}, headers=_auth())
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "VALIDATION_ERROR"


def test_project_detail_summary_and_unknown_slug() -> None:
    svc = StubService(projects=[{"id": "1", "name": "Demo", "slug": "demo", "description": "d", "created_at": "x"}])
    svc.summary_by_slug["demo"] = {"proposal": 2, "spec": 5}
    client = _client(svc)

    detail = client.get("/api/v1/projects/demo", headers=_auth())
    assert detail.status_code == 200
    assert detail.json()["summary"] == {"proposal": 2, "spec": 5}

    missing = client.get("/api/v1/projects/nope", headers=_auth())
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"


# ── Unit 2: artifacts read endpoints (artifact-management REQ-001/002) ───────


def test_artifacts_list_and_type_filter() -> None:
    svc = StubService(
        artifacts_by_slug={
            "demo": [
                {"id": "a1", "name": "s1", "type": "spec", "status": "draft", "metadata": {}, "updated_at": "t2"},
                {"id": "a2", "name": "t1", "type": "task", "status": "active", "metadata": {}, "updated_at": "t1"},
                {"id": "a3", "name": "t2", "type": "task", "status": "draft", "metadata": {}, "updated_at": "t0"},
            ]
        }
    )
    client = _client(svc)

    all_ = client.get("/api/v1/projects/demo/artifacts", headers=_auth())
    assert all_.status_code == 200
    assert len(all_.json()) == 3

    tasks = client.get("/api/v1/projects/demo/artifacts?type=task", headers=_auth())
    assert tasks.status_code == 200
    assert {a["name"] for a in tasks.json()} == {"t1", "t2"}


def test_get_single_artifact_and_unknown_id() -> None:
    svc = StubService(
        artifact_by_id={
            "a1": {
                "id": "a1",
                "name": "s1",
                "type": "spec",
                "status": "draft",
                "metadata": {"change_name": "x"},
                "content": "# Spec\nbody",
                "created_at": "c",
                "updated_at": "u",
            }
        }
    )
    client = _client(svc)

    ok = client.get("/api/v1/artifacts/a1", headers=_auth())
    assert ok.status_code == 200
    assert ok.json()["content"] == "# Spec\nbody"
    assert ok.json()["metadata"] == {"change_name": "x"}

    missing = client.get("/api/v1/artifacts/nope", headers=_auth())
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"


# ── Unit 3: rules listing endpoint (harness-rules-management REQ-001) ────────


def test_rules_default_excludes_disabled() -> None:
    svc = StubService(
        rules_by_slug={
            "demo": [
                {"id": "r1", "name": "a", "trigger": "on_apply", "category": "naming", "severity": "error", "instruction": "i", "enabled": True},
                {"id": "r2", "name": "b", "trigger": "on_apply", "category": "naming", "severity": "warning", "instruction": "i", "enabled": True},
                {"id": "r3", "name": "c", "trigger": "on_verify", "category": "verification", "severity": "info", "instruction": "i", "enabled": True},
                {"id": "r4", "name": "d", "trigger": "always", "category": "architecture", "severity": "error", "instruction": "i", "enabled": True},
                {"id": "r5", "name": "e", "trigger": "always", "category": "forbidden", "severity": "error", "instruction": "i", "enabled": False},
            ]
        }
    )
    client = _client(svc)

    default = client.get("/api/v1/projects/demo/rules", headers=_auth())
    assert default.status_code == 200
    assert len(default.json()) == 4

    all_ = client.get("/api/v1/projects/demo/rules?enabled_all=true", headers=_auth())
    assert all_.status_code == 200
    assert len(all_.json()) == 5
    assert all(r["enabled"] for r in all_.json() if r["name"] != "e")


# ── Unit 4: search endpoint (web-api-management REQ-005) ─────────────────────


def test_search_ranked_results_and_missing_q() -> None:
    svc = StubService(
        search_results=[
            {"type": "spec", "title": "harness", "snippet": "s", "project": "opensddrag", "score": 1.0, "slug": "harness-spec"},
            {"type": "task", "title": "harness task", "snippet": "s", "project": "opensddrag", "score": 0.5, "slug": "t1"},
        ]
    )
    client = _client(svc)

    ok = client.get("/api/v1/search?q=harness&limit=5", headers=_auth())
    assert ok.status_code == 200
    body = ok.json()
    assert len(body) == 2
    assert body[0]["score"] >= body[1]["score"]
    assert set(body[0]) == {"type", "title", "snippet", "project", "score", "slug"}

    missing = client.get("/api/v1/search", headers=_auth())
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "VALIDATION_ERROR"