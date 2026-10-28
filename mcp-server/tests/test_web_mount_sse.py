"""SSE mount tests: management REST + optional static UI (mcp-server REQ-011/012/016).

Spec refs:
    - web-management-system mcp-server delta REQ-012 Scenario "Routes mounted
      in SSE mode only" (stdio has no HTTP app; SSE mounts /api/v1).
    - REQ-016 Scenario "Static frontend serving" (SERVE_WEB_UI gates /).
    - REQ-011 Scenario "MCP transports unchanged" (the /mcp mount is preserved).
    - web-api-key-management REQ-005 (existing valid key still connects) and
      web-api-management delta REQ-001 (routes keep mounted beside keys routes).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import httpx
import pytest
from starlette.testclient import TestClient

from opensddrag.db import api_key_repository
from opensddrag.mcp import server as srv
from opensddrag.web.routes import build_routes


class DummyMCPApp:
    """Minimal ASGI app standing in for the MCP session manager."""

    async def __call__(self, scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"mcp"})


def _app(*, serve_web_ui: bool, static_dir: Path | None = None):
    return srv.build_http_app(
        mcp_app=DummyMCPApp(), serve_web_ui=serve_web_ui, static_dir=static_dir
    )


def test_sse_mounts_api_v1_and_mcp_without_static_by_default() -> None:
    app = _app(serve_web_ui=False)
    client = TestClient(app)

    # /api/v1 is mounted: the bearer dependency rejects unauthenticated calls.
    resp = client.get("/api/v1/projects")
    assert resp.status_code == 401
    assert "UNAUTHORIZED" in resp.text

    # /mcp mount is preserved.
    assert any(getattr(r, "path", None) == "/mcp" for r in app.routes)

    # No static UI mount when disabled → "/" is not served.
    assert client.get("/").status_code == 404


def test_sse_serves_static_ui_when_enabled(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>OK-UI</html>", encoding="utf-8")
    app = _app(serve_web_ui=True, static_dir=tmp_path)
    client = TestClient(app)

    root = client.get("/")
    assert root.status_code == 200
    assert "OK-UI" in root.text

    # API still takes precedence over the static catch-all.
    assert client.get("/api/v1/projects").status_code == 401


def test_mcp_path_without_slash_does_not_redirect() -> None:
    """POST /mcp must reach the transport. A 307 drops Cursor's Bearer token."""
    app = srv.build_http_app(
        mcp_app=DummyMCPApp(), serve_web_ui=False, auth_enabled=False
    )
    client = TestClient(app, follow_redirects=False)

    bare = client.post("/mcp")
    assert bare.status_code == 200
    assert bare.content == b"mcp"

    slashed = client.post("/mcp/")
    assert slashed.status_code == 200
    assert slashed.content == b"mcp"


def test_stdio_does_not_build_http_app() -> None:
    # REQ-012: stdio mode has no HTTP app — the /api/v1 routes only exist in SSE.
    assert "build_http_app" not in inspect.getsource(srv._main_stdio)
    assert "build_http_app" in inspect.getsource(srv._main_sse)


@pytest.mark.asyncio
async def test_mcp_bearer_key_works_with_keys_routes_mounted() -> None:
    """web-api-key-management REQ-005: with the keys routes shipped, a
    previously valid MCP Bearer key passes AuthMiddleware on both /mcp
    and /mcp/ (HTTP 200, no 307 dropping Authorization), and the
    management REST routes stay mounted in the same app.
    """
    key_record, plaintext = await api_key_repository.create_key(
        description="sse keys-shipped"
    )
    try:
        app = srv.build_http_app(mcp_app=DummyMCPApp(), serve_web_ui=False)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            for path in ("/mcp", "/mcp/"):
                resp = await client.post(
                    path, headers={"Authorization": f"Bearer {plaintext}"}
                )
                assert resp.status_code == 200
                assert resp.content == b"mcp"

            projects = await client.get("/api/v1/projects")
            assert projects.status_code == 401
            keys = await client.get("/api/v1/keys")
            assert keys.status_code == 401  # mounted and auth-wrapped
    finally:
        await api_key_repository.revoke_key(key_record.id)


@pytest.mark.asyncio
async def test_mcp_bearer_key_revoked_returns_401_with_keys_routes_mounted() -> None:
    """web-api-key-management REQ-003/REQ-005: a dashboard-revoked key
    yields 401 at /mcp inside the full app (middleware chain), not a
    redirect or crash.
    """
    key_record, plaintext = await api_key_repository.create_key(
        description="sse revoked-through-service"
    )
    await api_key_repository.revoke_key(key_record.id)
    app = srv.build_http_app(mcp_app=DummyMCPApp(), serve_web_ui=False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/mcp", headers={"Authorization": f"Bearer {plaintext}"}
        )
        assert resp.status_code == 401


def test_management_routes_mounted_beside_keys_routes() -> None:
    """web-api-management delta REQ-001: projects, artifacts, and rules
    routes are still mounted alongside the new keys routes.
    """
    routes = build_routes(object())  # handlers never invoked here
    paths = [getattr(route, "path", "") for route in routes]
    for prefix in (
        "/api/v1/keys",
        "/api/v1/projects",
        "/api/v1/artifacts",
        "/api/v1/projects/{slug}/rules",
    ):
        assert any(p.startswith(prefix) for p in paths), f"missing {prefix}"