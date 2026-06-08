from datetime import datetime, timedelta, timezone

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from opensddrag.db import api_key_repository
from opensddrag.mcp.auth import AuthMiddleware


async def _ok(request: Request):
    return JSONResponse({"ok": True, "project": getattr(request.state, "project_slug", None)})


def _make_app():
    return Starlette(
        routes=[Route("/test", _ok)],
        middleware=[Middleware(AuthMiddleware)],
    )


@pytest.fixture
def client():
    return TestClient(_make_app(), raise_server_exceptions=False)


@pytest.mark.asyncio
async def test_missing_header_returns_401(client):
    resp = client.get("/test")
    assert resp.status_code == 401
    assert resp.json()["error"] == "missing authorization header"


@pytest.mark.asyncio
async def test_invalid_key_returns_401(client):
    resp = client.get("/test", headers={"Authorization": "Bearer totally-fake-key"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["error"]


@pytest.mark.asyncio
async def test_valid_global_key_is_accepted():
    key_record, plaintext = await api_key_repository.create_key(description="middleware test")
    try:
        c = TestClient(_make_app(), raise_server_exceptions=False)
        resp = c.get("/test", headers={"Authorization": f"Bearer {plaintext}"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
    finally:
        await api_key_repository.revoke_key(key_record.id)


@pytest.mark.asyncio
async def test_revoked_key_returns_401():
    key_record, plaintext = await api_key_repository.create_key(description="revoked middleware test")
    await api_key_repository.revoke_key(key_record.id)

    c = TestClient(_make_app(), raise_server_exceptions=False)
    resp = c.get("/test", headers={"Authorization": f"Bearer {plaintext}"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["error"]


@pytest.mark.asyncio
async def test_expired_key_returns_401():
    past = datetime.now(tz=timezone.utc) - timedelta(days=1)
    key_record, plaintext = await api_key_repository.create_key(
        description="expired middleware test", expires_at=past
    )
    try:
        c = TestClient(_make_app(), raise_server_exceptions=False)
        resp = c.get("/test", headers={"Authorization": f"Bearer {plaintext}"})
        assert resp.status_code == 401
        assert resp.json()["error"] == "api key expired"
    finally:
        await api_key_repository.revoke_key(key_record.id)
