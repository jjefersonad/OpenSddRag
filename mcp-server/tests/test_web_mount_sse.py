"""SSE mount tests: management REST + optional static UI (mcp-server REQ-011/012/016).

Spec refs:
    - web-management-system mcp-server delta REQ-012 Scenario "Routes mounted
      in SSE mode only" (stdio has no HTTP app; SSE mounts /api/v1).
    - REQ-016 Scenario "Static frontend serving" (SERVE_WEB_UI gates /).
    - REQ-011 Scenario "MCP transports unchanged" (the /mcp mount is preserved).
"""

from __future__ import annotations

import inspect
from pathlib import Path

from starlette.testclient import TestClient

from opensddrag.mcp import server as srv


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