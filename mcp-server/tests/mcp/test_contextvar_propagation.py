"""Integration tests: ContextVar propagation from AuthMiddleware to the tool handler.

Spec refs:
    fix-multitenant-project-resolution-mcp-http-auth-spec
    REQ-001 scenario "Project state reaches the executor":
        AuthMiddleware sets the ContextVar; it is readable downstream.
    REQ-001 scenario "stdio caller unaffected":
        When the ContextVar is unset (no middleware), Caller.project_slug is None.
    ContextVar isolation: concurrent requests with different project slugs
        each see their own slug (PEP 567 / anyio task group context copy).

No real PostgreSQL: the DB layer (api_key_repository, project_repository)
is replaced with AsyncMock fakes.

Run with:
    pytest tests/mcp/test_contextvar_propagation.py -v
"""

from __future__ import annotations

import asyncio
import unittest.mock as mock
from uuid import UUID

import httpx
import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from opensddrag.mcp.auth import AuthMiddleware
from opensddrag.mcp.context import get_caller_project, set_caller_project
from opensddrag.mcp.server import MCPServerAdapter

# ── Constants ─────────────────────────────────────────────────────────────────

_PROJECT_A_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_PROJECT_B_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

_LOOKUP_PATH = "opensddrag.db.api_key_repository.lookup_by_hash"
_GET_PROJECT_PATH = "opensddrag.db.project_repository.get_project_by_id"

# ── Helpers ───────────────────────────────────────────────────────────────────


def _key_for_project(project_id: UUID):
    key = mock.MagicMock()
    key.project_id = project_id
    key.revoked_at = None
    key.expires_at = None
    return key


def _project(slug: str):
    p = mock.MagicMock()
    p.slug = slug
    return p


async def _slug_reader(request: Request) -> JSONResponse:
    """Minimal route that exposes the ContextVar value for assertions."""
    return JSONResponse({"project_slug": get_caller_project()})


def _build_app() -> Starlette:
    return Starlette(
        routes=[Route("/messages/", _slug_reader, methods=["POST", "GET"])],
        middleware=[Middleware(AuthMiddleware)],
    )


# ── Test 1: project state reaches the handler via ContextVar ──────────────────


@pytest.mark.asyncio
async def test_project_slug_propagated_via_contextvar():
    """
    REQ-001 'Project state reaches the executor':
    A request authenticated with a project-scoped API key bound to
    'test-project' results in get_caller_project() == 'test-project'
    inside the downstream handler.
    """
    with (
        mock.patch(
            _LOOKUP_PATH,
            new=mock.AsyncMock(return_value=_key_for_project(_PROJECT_A_ID)),
        ),
        mock.patch(
            _GET_PROJECT_PATH,
            new=mock.AsyncMock(return_value=_project("test-project")),
        ),
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_build_app()),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/messages/", headers={"Authorization": "Bearer fake-token"}
            )

    assert resp.status_code == 200
    assert resp.json()["project_slug"] == "test-project"


# ── Test 2: stdio path — ContextVar is None ───────────────────────────────────


def test_stdio_caller_has_no_project_slug():
    """
    REQ-001 'stdio caller unaffected':
    Without HTTP middleware, the ContextVar is at its default (None),
    and MCPServerAdapter._resolve_caller() returns a stdio Caller with
    project_slug=None.
    """
    fake_use_cases = mock.MagicMock()
    adapter = MCPServerAdapter(fake_use_cases)

    # ContextVar is at its default (never set in this synchronous test context)
    caller = adapter._resolve_caller()

    assert caller.caller_id == "stdio"
    assert caller.project_slug is None


# ── Test 3: ContextVar not leaked between concurrent async tasks ──────────────


@pytest.mark.asyncio
async def test_contextvar_isolated_between_concurrent_tasks():
    """
    ContextVar is not leaked: two concurrent async tasks each setting a
    different slug see only their own slug after an await yield.

    This verifies PEP 567 behaviour — asyncio.gather() copies the current
    context into each task, so mutations in one task are invisible to the other.
    """
    results: dict[str, str | None] = {}

    async def task(token: str, slug: str) -> None:
        set_caller_project(slug)
        await asyncio.sleep(0)  # yield so both tasks can interleave
        results[token] = get_caller_project()

    await asyncio.gather(
        task("a", "project-alpha"),
        task("b", "project-beta"),
    )

    assert results["a"] == "project-alpha"
    assert results["b"] == "project-beta"


# ── Test 4: two concurrent HTTP requests with different project slugs ─────────


@pytest.mark.asyncio
async def test_contextvar_isolated_between_concurrent_http_requests():
    """
    Two simultaneous HTTP requests with different project-scoped API keys
    each see their own project slug in the handler.
    """
    project_slugs_by_id = {
        _PROJECT_A_ID: "project-alpha",
        _PROJECT_B_ID: "project-beta",
    }

    async def fake_lookup(token: str):
        project_id = _PROJECT_A_ID if token == "token-a" else _PROJECT_B_ID
        return _key_for_project(project_id)

    async def fake_get_project(project_id: UUID):
        return _project(project_slugs_by_id[project_id])

    with (
        mock.patch(_LOOKUP_PATH, new=mock.AsyncMock(side_effect=fake_lookup)),
        mock.patch(_GET_PROJECT_PATH, new=mock.AsyncMock(side_effect=fake_get_project)),
    ):
        app = _build_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp_a, resp_b = await asyncio.gather(
                client.post("/messages/", headers={"Authorization": "Bearer token-a"}),
                client.post("/messages/", headers={"Authorization": "Bearer token-b"}),
            )

    assert resp_a.json()["project_slug"] == "project-alpha"
    assert resp_b.json()["project_slug"] == "project-beta"
