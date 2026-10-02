"""Unit tests for the /api/v1 Bearer-token auth dependency (web/deps.py).

Spec refs:
    web-management-system web-api-management delta REQ-002:
    - Scenario "Valid token accepted"
    - Scenario "Missing or invalid token"
    - Scenario "Server without configured token fails closed"

Uses Starlette TestClient against a minimal app that mounts the
dependency-wrapped endpoint exactly as the real routes will (backend-4).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient


def _make_app() -> Starlette:
    from opensddrag.web.deps import require_management_token

    async def ping(request):
        return JSONResponse({"pong": True})

    return Starlette(routes=[Route("/api/v1/ping", ping, methods=["GET"])])  # dependency wired by router code


@pytest.fixture()
def app_with_token():
    """Minimal app where the ping route is auth-wrapped; token = secret-token."""
    from opensddrag.web.deps import require_management_token

    async def ping(request):
        return JSONResponse({"pong": True})

    app = Starlette()
    app.router.routes.append(Route("/api/v1/ping", require_management_token(ping), methods=["GET"]))
    with patch("opensddrag.web.deps.settings") as mock_settings:
        mock_settings.management_token = "secret-token"
        mock_settings.web_origin = "http://localhost:3001"
        yield TestClient(app, raise_server_exceptions=True), app


@pytest.fixture()
def app_without_token():
    from opensddrag.web.deps import require_management_token

    async def ping(request):
        return JSONResponse({"pong": True})

    app = Starlette()
    app.router.routes.append(Route("/api/v1/ping", require_management_token(ping), methods=["GET"]))
    with patch("opensddrag.web.deps.settings") as mock_settings:
        mock_settings.management_token = None
        mock_settings.web_origin = "http://localhost:3001"
        yield TestClient(app, raise_server_exceptions=True), app


# ── Unit 1: require_management_token (valid / absent / malformed / wrong) ────


def test_valid_token_passes(app_with_token) -> None:
    client, _ = app_with_token
    resp = client.get("/api/v1/ping", headers={"Authorization": "Bearer secret-token"})
    assert resp.status_code == 200
    assert resp.json() == {"pong": True}


def test_missing_header_rejected(app_with_token) -> None:
    client, _ = app_with_token
    resp = client.get("/api/v1/ping")
    assert resp.status_code == 401
    assert resp.json() == {"error": {"code": "UNAUTHORIZED", "message": "Missing bearer token"}}


def test_malformed_header_rejected(app_with_token) -> None:
    client, _ = app_with_token
    resp = client.get("/api/v1/ping", headers={"Authorization": "Token abc"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert "bearer" in body["error"]["message"].lower()


def test_wrong_token_rejected(app_with_token) -> None:
    client, _ = app_with_token
    resp = client.get("/api/v1/ping", headers={"Authorization": "Bearer not-the-token"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


# ── Unit 2: fail-closed when MANAGEMENT_API_TOKEN unset ──────────────────────


def test_fail_closed_when_token_unset(app_without_token) -> None:
    client, _ = app_without_token
    resp = client.get("/api/v1/ping", headers={"Authorization": "Bearer anything"})
    assert resp.status_code == 401
    assert resp.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Management API is disabled (no MANAGEMENT_API_TOKEN configured)",
        }
    }


def test_fail_closed_without_header(app_without_token) -> None:
    client, _ = app_without_token
    resp = client.get("/api/v1/ping")
    assert resp.status_code == 401


# ── CORS wiring helper (REQ-013 / design D4) ────────────────────────────────


def test_wire_cors_uses_settings_origin() -> None:
    from opensddrag.web.deps import wire_cors

    class FakeSettings:
        web_origin = "http://app.example.com"

    middlewares = wire_cors(FakeSettings())
    assert middlewares, "expected at least one middleware instance"