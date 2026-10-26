"""Mutation-router tests for the /api/v1 management REST adapter.

Spec refs:
    - web-api-management REQ-004 (task {done} merge) / REQ-006 (rule toggle)
    - harness-rules-management REQ-002 (create + enum validation) / REQ-003 (toggle)
    - artifact-management REQ-003 (create) / REQ-004 (update) / REQ-005 (relationships)

The routers depend on `ManagementServiceProtocol`; a deterministic stub is
injected (delivery adapters are exercised through their public HTTP API).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from opensddrag.core.domain.errors import (
    ManagementValidationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from opensddrag.core.domain.rule_constants import (
    VALID_RULE_CATEGORIES,
    VALID_RULE_SEVERITIES,
    VALID_RULE_TRIGGERS,
)
from opensddrag.web.routes import build_routes

TOKEN = "test-token"
REL_VALID = ("implements", "depends_on", "relates_to")


class FakeSettings:
    management_token = TOKEN
    web_origin = "http://localhost:3001"


class StubService:
    """Deterministic in-memory stub covering the mutation surface."""

    def __init__(self, *, tasks=None, rules=None, artifacts=None):
        self.tasks = tasks or {}
        self.rules = rules or {}
        self.artifacts = artifacts or {}
        self.projects: dict = {}
        self.links: list[dict] = []

    # ── tasks ──
    async def set_task_done(self, slug, task_id, done):
        task = self.tasks.get(task_id)
        if task is None or task["project_slug"] != slug:
            raise ResourceNotFoundError(f"task {task_id!r} not found in project {slug!r}")
        task["metadata"] = {**task["metadata"], "done": done}
        return task

    # ── rules ──
    async def create_rule(self, slug, name, trigger, category, severity, instruction):
        if trigger not in VALID_RULE_TRIGGERS:
            raise ManagementValidationError("invalid trigger", details=list(VALID_RULE_TRIGGERS))
        if category not in VALID_RULE_CATEGORIES:
            raise ManagementValidationError("invalid category", details=list(VALID_RULE_CATEGORIES))
        if severity not in VALID_RULE_SEVERITIES:
            raise ManagementValidationError("invalid severity", details=list(VALID_RULE_SEVERITIES))
        rule = {
            "id": f"r-{len(self.rules.get(slug, [])) + 1}",
            "name": name,
            "trigger": trigger,
            "category": category,
            "severity": severity,
            "instruction": instruction,
            "enabled": True,
        }
        self.rules.setdefault(slug, []).append(rule)
        return rule

    async def set_rule_enabled(self, slug, rule_id, enabled):
        for rule in self.rules.get(slug, []):
            if rule["id"] == rule_id:
                rule["enabled"] = enabled  # idempotent
                return rule
        raise ResourceNotFoundError(f"rule {rule_id!r} not found")

    async def list_rules(self, slug, enabled_all=False):
        rules = list(self.rules.get(slug, []))
        return rules if enabled_all else [r for r in rules if r["enabled"]]

    # ── artifacts ──
    async def create_artifact(self, slug, name, type_, content, metadata):
        if any(a["name"] == name and a["project_slug"] == slug for a in self.artifacts.values()):
            raise ResourceConflictError(f"artifact name {name!r} already exists")
        art = {
            "id": f"a-{len(self.artifacts) + 1}",
            "name": name,
            "type": type_,
            "status": "draft",
            "content": content,
            "metadata": metadata or {},
            "project_slug": slug,
        }
        self.artifacts[art["id"]] = art
        return art

    async def update_artifact(self, artifact_id, content, metadata, status, name=None):
        art = self.artifacts.get(artifact_id)
        if art is None:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")
        if content is not None:
            art["content"] = content
        if metadata is not None:
            art["metadata"] = {**art["metadata"], **metadata}
        if status is not None:
            art["status"] = status
        if name is not None:
            art["name"] = name
        return art

    async def delete_artifact(self, artifact_id):
        art = self.artifacts.pop(artifact_id, None)
        if art is None:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")
        return {"deleted": True, "id": artifact_id}

    async def update_project(self, slug, name=None, description=None, language=None, new_slug=None):
        project = self.projects.get(slug) if hasattr(self, "projects") else None
        if project is None:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        if new_slug and new_slug != slug and new_slug in self.projects:
            raise ResourceConflictError(f"project slug {new_slug!r} already exists")
        if name is not None:
            project["name"] = name
        if description is not None:
            project["description"] = description
        if language is not None:
            project["language"] = language
        if new_slug and new_slug != slug:
            self.projects.pop(slug)
            project["slug"] = new_slug
            self.projects[new_slug] = project
        return project

    async def delete_project(self, slug):
        project = self.projects.pop(slug, None) if hasattr(self, "projects") else None
        if project is None:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        return {"deleted": True, "slug": slug}

    async def link_artifact(self, artifact_id, relationship_type, target_name, target_id):
        if relationship_type not in REL_VALID:
            raise ManagementValidationError(
                "invalid relationship_type", details=list(REL_VALID)
            )
        link = {
            "source_id": artifact_id,
            "target": target_id or target_name,
            "relationship_type": relationship_type,
        }
        self.links.append(link)
        return link

    async def list_api_keys(self, project_slug=None, include_revoked=False, scope=None):
        return []

    async def create_api_key(self, description="", project_slug=None, expires_at=None):
        if project_slug == "missing":
            raise ResourceNotFoundError(f"project {project_slug!r} not found")
        if expires_at == "not-a-date":
            raise ManagementValidationError("expires_at must be an ISO date or datetime")
        key = {
            "id": f"k-{len(getattr(self, 'api_keys', [])) + 1}",
            "prefix": "aabbccdd",
            "description": description,
            "project_slug": project_slug,
            "created_at": "2026-10-25T00:00:00+00:00",
            "expires_at": expires_at,
            "revoked_at": None,
            "status": "active",
            "key": "plain-text-once",
        }
        self.api_keys = getattr(self, "api_keys", [])
        self.api_keys.append({k: v for k, v in key.items() if k != "key"})
        return key

    async def revoke_api_key(self, key_id):
        for item in getattr(self, "api_keys", []):
            if item["id"] == key_id:
                item["status"] = "revoked"
                item["revoked_at"] = "2026-10-25T12:00:00+00:00"
                return item
        raise ResourceNotFoundError(f"api key {key_id!r} not found")


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    import opensddrag.web.deps as deps

    monkeypatch.setattr(deps, "settings", FakeSettings())


def _client(service) -> TestClient:
    return TestClient(Starlette(routes=build_routes(service)))


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


# ── Unit 1: patch_task_done (web-api-management REQ-004) ─────────────────────


def test_patch_task_done_merges_metadata_and_cross_project_404() -> None:
    svc = StubService(
        tasks={
            "t1": {
                "id": "t1",
                "project_slug": "a",
                "name": "task-1",
                "type": "task",
                "status": "active",
                "metadata": {"test_status": "passing"},
            }
        }
    )
    client = _client(svc)

    ok = client.patch("/api/v1/projects/a/tasks/t1", json={"done": True}, headers=_auth())
    assert ok.status_code == 200
    assert ok.json()["metadata"] == {"test_status": "passing", "done": True}

    cross = client.patch("/api/v1/projects/b/tasks/t1", json={"done": True}, headers=_auth())
    assert cross.status_code == 404
    assert cross.json()["error"]["code"] == "NOT_FOUND"


# ── Unit 2: rules create + toggle (harness REQ-002/003, web-api REQ-006) ─────


def test_rules_create_validates_enums_and_toggle_is_idempotent() -> None:
    svc = StubService(rules={"a": []})
    client = _client(svc)

    bad = client.post(
        "/api/v1/projects/a/rules",
        json={"name": "x", "trigger": "sometimes", "category": "naming", "severity": "error", "instruction": "i"},
        headers=_auth(),
    )
    assert bad.status_code == 422
    assert "always" in bad.json()["error"]["details"]

    created = client.post(
        "/api/v1/projects/a/rules",
        json={"name": "x", "trigger": "on_apply", "category": "naming", "severity": "error", "instruction": "i"},
        headers=_auth(),
    )
    assert created.status_code == 201
    assert created.json()["enabled"] is True
    rule_id = created.json()["id"]

    off = client.patch(f"/api/v1/projects/a/rules/{rule_id}", json={"enabled": False}, headers=_auth())
    assert off.status_code == 200
    assert off.json()["enabled"] is False

    default = client.get("/api/v1/projects/a/rules", headers=_auth())
    assert default.status_code == 200
    assert default.json() == []

    all_ = client.get("/api/v1/projects/a/rules?enabled_all=true", headers=_auth())
    assert [r["enabled"] for r in all_.json()] == [False]

    again = client.patch(f"/api/v1/projects/a/rules/{rule_id}", json={"enabled": False}, headers=_auth())
    assert again.status_code == 200
    assert again.json()["enabled"] is False


# ── Unit 3: artifact mutations (artifact-management REQ-003/004/005) ─────────


def test_artifact_create_update_and_relationship() -> None:
    svc = StubService(artifacts={"a-1": {"id": "a-1", "name": "spec-x", "type": "spec", "status": "draft", "content": "old", "metadata": {"keep": 1}, "project_slug": "a"}})
    # make a-1 the only existing artifact so create's duel check is predictable
    svc.artifacts = {}
    client = _client(svc)

    created = client.post(
        "/api/v1/projects/a/artifacts",
        json={"name": "s1", "type": "spec", "content": "# Spec"},
        headers=_auth(),
    )
    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    assert created.json()["type"] == "spec"

    dup = client.post(
        "/api/v1/projects/a/artifacts",
        json={"name": "s1", "type": "spec", "content": "# Spec again"},
        headers=_auth(),
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "CONFLICT"

    art_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/artifacts/{art_id}",
        json={"content": "# Spec v2", "metadata": {"note": "edited"}},
        headers=_auth(),
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "# Spec v2"
    assert updated.json()["metadata"] == {"note": "edited"}

    linked = client.post(
        f"/api/v1/artifacts/{art_id}/relationships",
        json={"relationship_type": "implements", "target_name": "spec-x"},
        headers=_auth(),
    )
    assert linked.status_code == 201
    assert svc.links[0]["relationship_type"] == "implements"

    bad_rel = client.post(
        f"/api/v1/artifacts/{art_id}/relationships",
        json={"relationship_type": "friend_of", "target_name": "spec-x"},
        headers=_auth(),
    )
    assert bad_rel.status_code == 422
    assert "implements" in bad_rel.json()["error"]["details"]


def test_update_artifact_status_and_metadata_preserved() -> None:
    svc = StubService(
        artifacts={
            "a-1": {
                "id": "a-1",
                "name": "s1",
                "type": "spec",
                "status": "draft",
                "content": "old",
                "metadata": {"keep": 1, "note": "x"},
                "project_slug": "a",
            }
        }
    )
    client = _client(svc)

    # metadata MERGE (not replace): "keep" survives, "note" overwritten
    resp = client.patch(
        "/api/v1/artifacts/a-1",
        json={"metadata": {"note": "updated"}, "status": "active"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["metadata"] == {"keep": 1, "note": "updated"}
    assert resp.json()["status"] == "active"
    # content untouched when not provided
    assert resp.json()["content"] == "old"


def test_project_update_and_delete_and_artifact_delete() -> None:
    svc = StubService()
    svc.projects = {"demo": {"id": "1", "name": "Demo", "slug": "demo", "description": ""}}
    svc.artifacts = {"a-1": {"id": "a-1", "name": "s1", "type": "spec", "status": "draft", "content": "old", "metadata": {}, "project_slug": "demo"}}
    client = _client(svc)

    renamed = client.patch(
        "/api/v1/projects/demo",
        json={"name": "Demo two", "slug": "demo-two"},
        headers=_auth(),
    )
    assert renamed.status_code == 200
    assert renamed.json()["slug"] == "demo-two"
    assert renamed.json()["name"] == "Demo two"

    missing = client.delete("/api/v1/projects/missing", headers=_auth())
    assert missing.status_code == 404

    removed = client.delete("/api/v1/projects/demo-two", headers=_auth())
    assert removed.status_code == 200
    assert removed.json()["deleted"] is True

    gone = client.delete("/api/v1/artifacts/a-1", headers=_auth())
    assert gone.status_code == 200
    assert gone.json() == {"deleted": True, "id": "a-1"}
    assert "a-1" not in svc.artifacts

    again = client.delete("/api/v1/artifacts/a-1", headers=_auth())
    assert again.status_code == 404


def test_create_and_revoke_api_key() -> None:
    svc = StubService()
    client = _client(svc)

    created = client.post(
        "/api/v1/keys",
        json={"description": "Cursor jeff_ai", "project_slug": "jeff-ai"},
        headers=_auth(),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["key"] == "plain-text-once"
    assert body["prefix"] == "aabbccdd"
    assert body["project_slug"] == "jeff-ai"
    assert "key_hash" not in body

    missing_project = client.post(
        "/api/v1/keys",
        json={"description": "x", "project_slug": "missing"},
        headers=_auth(),
    )
    assert missing_project.status_code == 404

    revoked = client.post(f"/api/v1/keys/{body['id']}/revoke", headers=_auth())
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert "key" not in revoked.json()

    unknown = client.post("/api/v1/keys/nope/revoke", headers=_auth())
    assert unknown.status_code == 404


def test_create_api_key_rejects_bad_slug_and_expiry() -> None:
    svc = StubService()
    client = _client(svc)

    bad_slug = client.post(
        "/api/v1/keys",
        json={"project_slug": "Not A Slug"},
        headers=_auth(),
    )
    assert bad_slug.status_code == 422

    bad_date = client.post(
        "/api/v1/keys",
        json={"expires_at": "not-a-date"},
        headers=_auth(),
    )
    assert bad_date.status_code == 422