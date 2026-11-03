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

from opensddrag.core.domain.change_pages import paginate
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
        self.bundles: dict[tuple[str, str], dict] = {}
        self.changes_by_slug: dict[str, list] = {}
        self.api_keys: list[dict] = []

    async def list_projects(self):
        return list(self.projects)

    async def create_project(self, name, slug, description="", language=""):
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

    async def list_artifacts(self, slug, type_filter=None, flow_filter=None):
        if slug not in self.artifacts_by_slug:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        items = list(self.artifacts_by_slug[slug])
        if type_filter:
            items = [a for a in items if a["type"] == type_filter]
        if flow_filter:
            items = [a for a in items if a.get("flow") == flow_filter]
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

    async def get_change_bundle(self, slug, change):
        if (slug, change) not in self.bundles:
            raise ResourceNotFoundError(f"change {change!r} not found in project {slug!r}")
        return self.bundles[(slug, change)]

    async def list_changes(self, slug, page: int = 1, page_size: int = 8):
        if slug not in self.changes_by_slug:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        return paginate(list(self.changes_by_slug[slug]), page, page_size)

    async def list_api_keys(self, project_slug=None, include_revoked=False, scope=None):
        items = list(self.api_keys)
        if project_slug:
            items = [k for k in items if k.get("project_slug") == project_slug]
        if scope == "global":
            items = [k for k in items if not k.get("project_slug")]
        if not include_revoked:
            items = [k for k in items if k.get("status") != "revoked"]
        return items


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

# ── Flow registry endpoint (web-ui-design-alignment, web-api delta REQ-008) ──


class FlowsStubService(StubService):
    def __init__(self, *, flows=None, **kwargs):
        super().__init__(**kwargs)
        self.flows = flows if flows is not None else []

    async def list_flows(self):
        return list(self.flows)


def test_flows_endpoint_lists_registered_flows_with_lifecycle() -> None:
    svc = FlowsStubService(
        flows=[
            {
                "flow": "sdd",
                "kinds": [{"kind": "proposal", "rules": {}}],
                "lifecycle": [{"name": "Propose", "kinds": ["proposal"]}],
                "harness_triggers": ["on_spec"],
                "registered_at": "2026-01-01T00:00:00Z",
            },
            {
                "flow": "bare",
                "kinds": [{"kind": "note", "rules": {}}],
                "lifecycle": None,
                "harness_triggers": [],
                "registered_at": "2026-01-01T00:00:00Z",
            },
        ]
    )
    client = _client(svc)

    resp = client.get("/api/v1/flows", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert [f["flow"] for f in body] == ["sdd", "bare"]
    assert body[0]["lifecycle"] == [{"name": "Propose", "kinds": ["proposal"]}]
    # Flow without lifecycle exposes null (REQ-008 Scenario 3)
    assert body[1]["lifecycle"] is None


def test_flows_endpoint_requires_token() -> None:
    svc = FlowsStubService(flows=[])
    client = _client(svc)
    resp = client.get("/api/v1/flows")
    assert resp.status_code == 401
    assert "UNAUTHORIZED" in resp.text


# ── Artifact flow field + filter (web-api delta REQ-009) ─────────────────────


def test_artifacts_flow_filter_and_field() -> None:
    svc = StubService(
        artifacts_by_slug={
            "demo": [
                {"id": "1", "name": "p", "type": "proposal", "status": "draft", "flow": "sdd", "metadata": {}, "created_at": None, "updated_at": None},
                {"id": "2", "name": "d", "type": "doc", "status": "draft", "flow": "docs", "metadata": {}, "created_at": None, "updated_at": None},
            ]
        }
    )
    client = _client(svc)

    # list_artifacts signature gains flow_filter — stub falls back.
    async def list_artifacts_flow(slug, type_filter=None, flow_filter=None):
        items = list(svc.artifacts_by_slug[slug])
        if flow_filter:
            items = [a for a in items if a["flow"] == flow_filter]
        return items

    svc.list_artifacts = list_artifacts_flow  # type: ignore[method-assign]

    both = client.get("/api/v1/projects/demo/artifacts", headers=_auth())
    assert both.status_code == 200
    assert len(both.json()) == 2
    assert {a["flow"] for a in both.json()} == {"sdd", "docs"}

    scoped = client.get("/api/v1/projects/demo/artifacts?flow=sdd", headers=_auth())
    assert scoped.status_code == 200
    assert [a["flow"] for a in scoped.json()] == ["sdd"]


# ── Working context endpoint (project delta REQ-003 via D4) ──────────────────


class SessionStubService(FlowsStubService):
    def __init__(self, *, session=None, **kwargs):
        super().__init__(**kwargs)
        self.session = session

    async def get_session(self, slug):
        if slug not in self.artifacts_by_slug:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        return self.session


def test_session_endpoint_returns_working_context() -> None:
    svc = SessionStubService(
        session={
            "active_artifacts": [{"id": "a1", "name": "p", "type": "proposal"}],
            "note": "working on proposal",
        },
        artifacts_by_slug={"demo": []},
    )
    client = _client(svc)
    resp = client.get("/api/v1/projects/demo/session", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_artifacts"] == [{"id": "a1", "name": "p", "type": "proposal"}]
    assert body["note"] == "working on proposal"

    missing = client.get("/api/v1/projects/none/session", headers=_auth())
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"


# ── Tree endpoint route (web-artifact-hierarchy REQ-010) ────────────────────


class TreeStubService(FlowsStubService):
    async def get_tree(self, slug):
        if slug != "demo":
            raise ResourceNotFoundError(f"project {slug!r} not found")
        return {
            "change": "add-x",
            "flows": [
                {
                    "flow": "sdd",
                    "nodes": [
                        {"id": "n1", "name": "add-x-proposal", "type": "proposal", "status": "active", "depth": 0, "flow": "sdd"},
                        {"id": "n2", "name": "alpha-spec", "type": "spec", "status": "draft", "depth": 1, "flow": "sdd"},
                    ],
                    "edges": [{"source": "n2", "target": "n1", "relationship_type": "implements"}],
                }
            ],
        }


def test_tree_endpoint_route() -> None:
    svc = TreeStubService()
    client = _client(svc)

    ok = client.get("/api/v1/projects/demo/tree", headers=_auth())
    assert ok.status_code == 200
    body = ok.json()
    assert body["change"] == "add-x"
    assert body["flows"][0]["nodes"][0]["depth"] == 0
    assert body["flows"][0]["edges"][0]["relationship_type"] == "implements"

    missing = client.get("/api/v1/projects/none/tree", headers=_auth())
    assert missing.status_code == 404

    unauth = client.get("/api/v1/projects/demo/tree")
    assert unauth.status_code == 401


# ── include=content opt-in (web-ui-prototype-fidelity, web-api REQ-013) ─────


class ContentStubService(StubService):
    """Stub whose list_artifacts accepts the opt-in `include_content` keyword."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calls: list[dict] = []

    async def list_artifacts(
        self, slug, type_filter=None, flow_filter=None, include_content=False
    ):
        self.calls.append({"slug": slug, "include_content": include_content})
        items = await super().list_artifacts(slug, type_filter, flow_filter)
        if include_content:
            return [{**a, "content": f"# {a['name']}"} for a in items]
        return items


def _content_service() -> ContentStubService:
    return ContentStubService(
        artifacts_by_slug={"demo": [{"id": "a1", "name": "spec-a", "type": "spec", "status": "active"}]}
    )


def test_artifacts_include_content_is_forwarded_to_the_service() -> None:
    svc = _content_service()
    resp = _client(svc).get(
        "/api/v1/projects/demo/artifacts?type=spec&include=content", headers=_auth()
    )
    assert resp.status_code == 200
    assert svc.calls == [{"slug": "demo", "include_content": True}]
    assert resp.json()[0]["content"] == "# spec-a"


def test_artifacts_default_list_does_not_pass_the_keyword() -> None:
    # The base StubService keeps the OLD signature (no include_content): the
    # router must not pass the new keyword unless the client asked for it.
    svc = StubService(
        artifacts_by_slug={"demo": [{"id": "a1", "name": "spec-a", "type": "spec", "status": "active"}]}
    )
    resp = _client(svc).get("/api/v1/projects/demo/artifacts?type=spec", headers=_auth())
    assert resp.status_code == 200
    assert "content" not in resp.json()[0]


def test_artifacts_include_with_other_value_is_422() -> None:
    svc = _content_service()
    resp = _client(svc).get("/api/v1/projects/demo/artifacts?include=foo", headers=_auth())
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    assert svc.calls == []


# ── Change bundle stub (web-change-reader D7) ────────────────────────────────


def test_stub_get_change_bundle_returns_payload_or_not_found() -> None:
    import asyncio

    svc = StubService()
    payload = {
        "change": "chg-a",
        "flow": "sdd",
        "proposal": {"name": "chg-a-proposal", "content": "# P"},
        "design": None,
        "specs": [],
        "tasks": [],
        "task_count": 0,
    }
    svc.bundles[("demo", "chg-a")] = payload
    assert asyncio.run(svc.get_change_bundle("demo", "chg-a")) == payload
    with pytest.raises(ResourceNotFoundError):
        asyncio.run(svc.get_change_bundle("demo", "missing"))


# ── Change bundle HTTP route (web-change-reader backend-2, REQ-014) ──────────


_BUNDLE = {
    "change": "web-change-reader",
    "flow": "sdd",
    "proposal": {
        "id": "p1",
        "name": "web-change-reader-proposal",
        "type": "proposal",
        "content": "# Why\nHuman can read the change.",
    },
    "design": {
        "id": "d1",
        "name": "web-change-reader-design",
        "type": "design",
        "content": "# Context\nREST bundle, not MCP.",
    },
    "specs": [
        {"id": "s1", "name": "alpha-spec", "type": "spec", "content": "# Alpha"},
        {"id": "s2", "name": "beta-spec", "type": "spec", "content": "# Beta"},
    ],
    "tasks": [
        {"name": "t1", "status": "archived", "content": "## Goal\ng1", "done": True},
        {"name": "t2", "status": "archived", "content": "## Goal\ng2", "done": True},
        {"name": "t3", "status": "archived", "content": "## Goal\ng3", "done": True},
        {"name": "t4", "status": "draft", "content": "## Goal\ng4", "done": False},
    ],
    "task_count": 4,
}


def test_get_change_bundle_http_returns_bodies() -> None:
    svc = StubService()
    svc.bundles[("demo", "web-change-reader")] = _BUNDLE
    resp = _client(svc).get(
        "/api/v1/projects/demo/changes/web-change-reader", headers=_auth()
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["proposal"]["content"]
    assert body["design"]["content"]
    assert all("content" in spec for spec in body["specs"])
    assert all("content" in task for task in body["tasks"])
    assert body["task_count"] == 4
    assert body["task_count"] == len(body["tasks"])


def test_get_change_bundle_http_unknown_is_404() -> None:
    svc = StubService()
    missing_change = _client(svc).get(
        "/api/v1/projects/demo/changes/does-not-exist", headers=_auth()
    )
    assert missing_change.status_code == 404
    payload = missing_change.json()
    assert payload["error"]["code"] == "NOT_FOUND"
    assert "proposal" not in payload
    assert "specs" not in payload

    missing_slug = _client(svc).get(
        "/api/v1/projects/nope/changes/web-change-reader", headers=_auth()
    )
    assert missing_slug.status_code == 404
    assert missing_slug.json()["error"]["code"] == "NOT_FOUND"

    unauth = _client(svc).get("/api/v1/projects/demo/changes/web-change-reader")
    assert unauth.status_code == 401


def test_list_changes_http_shape_unchanged() -> None:
    svc = StubService()
    svc.changes_by_slug["demo"] = [
        {
            "change": "chg-a",
            "flow": "sdd",
            "started_at": "2026-10-01T09:00:00Z",
            "updated_at": "2026-10-08T11:00:00Z",
            "task_progress": {"done": 0, "total": 1},
            "phases": [{"name": "Propose", "status": "active", "desc": "d"}],
        }
    ]
    resp = _client(svc).get("/api/v1/projects/demo/changes?page=1&page_size=8", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["items"][0]["change"] == "chg-a"
    assert "content" not in body["items"][0]
    assert {"change", "flow", "updated_at", "task_progress", "phases"} <= set(body["items"][0])

    bad = _client(svc).get("/api/v1/projects/demo/changes?page=0", headers=_auth())
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_changes_http_pages_newest_first() -> None:
    svc = StubService()
    svc.changes_by_slug["demo"] = [
        {"change": "older", "flow": "sdd", "updated_at": "2026-10-01T00:00:00Z", "task_progress": {"done": 0, "total": 0}, "phases": []},
        {"change": "newest", "flow": "sdd", "updated_at": "2026-10-08T00:00:00Z", "task_progress": {"done": 0, "total": 0}, "phases": []},
    ]
    client = _client(svc)
    first = client.get("/api/v1/projects/demo/changes?page=1&page_size=1", headers=_auth())
    assert first.status_code == 200
    assert first.json()["total"] == 2
    assert first.json()["items"][0]["change"] == "newest"
    second = client.get("/api/v1/projects/demo/changes?page=2&page_size=1", headers=_auth())
    assert second.json()["items"][0]["change"] == "older"


def test_list_api_keys_filters_and_hides_secrets() -> None:
    svc = StubService()
    svc.api_keys = [
        {
            "id": "1",
            "prefix": "aaa11111",
            "description": "global",
            "project_slug": None,
            "status": "active",
        },
        {
            "id": "2",
            "prefix": "bbb22222",
            "description": "jeff",
            "project_slug": "jeff-ai",
            "status": "active",
        },
        {
            "id": "3",
            "prefix": "ccc33333",
            "description": "old",
            "project_slug": None,
            "status": "revoked",
        },
    ]
    client = _client(svc)

    active = client.get("/api/v1/keys", headers=_auth())
    assert active.status_code == 200
    assert [k["id"] for k in active.json()] == ["1", "2"]
    assert all("key" not in k and "key_hash" not in k for k in active.json())

    scoped = client.get("/api/v1/keys?project=jeff-ai", headers=_auth())
    assert [k["id"] for k in scoped.json()] == ["2"]

    global_only = client.get("/api/v1/keys?scope=global", headers=_auth())
    assert [k["id"] for k in global_only.json()] == ["1"]

    with_revoked = client.get("/api/v1/keys?include_revoked=true", headers=_auth())
    assert [k["id"] for k in with_revoked.json()] == ["1", "2", "3"]

    unauth = client.get("/api/v1/keys")
    assert unauth.status_code == 401
