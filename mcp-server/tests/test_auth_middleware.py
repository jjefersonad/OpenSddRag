"""AuthMiddleware tests.

The middleware resolves API keys through the shared async psycopg pool.
These tests therefore use an in-loop ``httpx.AsyncClient`` with
``ASGITransport`` instead of Starlette's ``TestClient``: ``TestClient``
spawns a portal thread with its own event loop, so the session-scoped
pool (opened by the ``db_pool`` fixture in the pytest-asyncio loop) is
unreachable from the app and every DB hit raises
``psycopg_pool.PoolTimeout``. Running the ASGI app in the test's own
loop keeps the pool and the app on the same loop — the same pattern
already used by ``tests/mcp/test_contextvar_propagation.py``.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.db import api_key_repository
from opensddrag.mcp.auth import AuthMiddleware


async def _ok(request: Request):
    return JSONResponse({"ok": True, "project": getattr(request.state, "project_slug", None)})


def _make_app() -> Starlette:
    return Starlette(
        routes=[Route("/test", _ok)],
        middleware=[Middleware(AuthMiddleware)],
    )


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_make_app()),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_missing_header_returns_401():
    async with _client() as client:
        resp = await client.get("/test")
    assert resp.status_code == 401
    assert resp.json()["error"] == "missing authorization header"


@pytest.mark.asyncio
async def test_invalid_key_returns_401():
    async with _client() as client:
        resp = await client.get("/test", headers={"Authorization": "Bearer totally-fake-key"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["error"]


@pytest.mark.asyncio
async def test_valid_global_key_is_accepted():
    key_record, plaintext = await api_key_repository.create_key(description="middleware test")
    try:
        async with _client() as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {plaintext}"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
    finally:
        await api_key_repository.revoke_key(key_record.id)


@pytest.mark.asyncio
async def test_revoked_key_returns_401():
    key_record, plaintext = await api_key_repository.create_key(description="revoked middleware test")
    await api_key_repository.revoke_key(key_record.id)

    async with _client() as client:
        resp = await client.get("/test", headers={"Authorization": f"Bearer {plaintext}"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["error"]


@pytest.mark.asyncio
async def test_expired_key_returns_401():
    past = datetime.now(tz=timezone.utc) - timedelta(days=1)
    key_record, plaintext = await api_key_repository.create_key(
        description="expired middleware test", expires_at=past
    )
    try:
        async with _client() as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {plaintext}"})
        assert resp.status_code == 401
        assert resp.json()["error"] == "api key expired"
    finally:
        await api_key_repository.revoke_key(key_record.id)
