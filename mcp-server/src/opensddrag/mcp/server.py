"""OpenSddRag MCP Server — MCP protocol adapter backed by the use-case layer.

All 23 tools flow through `ExecuteToolUseCase` (auth → rate-limit →
validate → execute → log). Unknown tool names return a structured
`{"error": {"code": "TOOL_NOT_FOUND", ...}}` envelope.
"""

import asyncio
import json
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

from opensddrag.config import settings
from opensddrag.infrastructure.bootstrap import bootstrap, shutdown
from opensddrag.infrastructure.mcp_resources import (
    list_project_resources,
    read_artifact_resource,
    read_project_resource,
)

from opensddrag.core.domain.permission import Permission
from opensddrag.core.domain.response import Response
from opensddrag.core.ports.authentication import Caller
from opensddrag.infrastructure.composition import UseCases, build_use_cases
from opensddrag.mcp.context import get_caller_project
from opensddrag.infrastructure.pg.tool_executors import EXECUTORS, PgToolExecutor

server = Server("opensddrag")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _text(content: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=content)]


def _json(data: Any) -> list[types.TextContent]:
    return _text(json.dumps(data, default=str, indent=2, ensure_ascii=False))


# ── MCP protocol adapter ──────────────────────────────────────────────────────

class MCPServerAdapter:
    def __init__(self, use_cases: UseCases) -> None:
        self._use_cases = use_cases

    def _resolve_caller(self) -> Caller:
        slug = get_caller_project()
        if slug is not None:
            return Caller(caller_id="http", permission=Permission.ADMIN, project_slug=slug)
        return Caller(caller_id="stdio", permission=Permission.ADMIN)

    async def list_tools(self) -> list[types.Tool]:
        caller = self._resolve_caller()
        domain_tools = self._use_cases.list_tools.list_for(caller.permission)
        return [
            types.Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.input_schema,
            )
            for tool in domain_tools
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[types.TextContent]:
        caller = self._resolve_caller()
        response = await self._use_cases.execute_tool.execute(name, arguments, caller)
        return self._serialize_response(response)

    def _serialize_response(self, response: Response) -> list[types.TextContent]:
        if response.is_ok:
            if isinstance(response.value, str):
                return _text(response.value)
            return _json(response.value)
        error: dict[str, Any] = {"code": response.code, "message": response.message}
        if response.details is not None:
            error["details"] = response.details
        return _json({"error": error})


_adapter: MCPServerAdapter | None = None


def get_adapter() -> MCPServerAdapter:
    global _adapter
    if _adapter is None:
        pg_executor = PgToolExecutor()
        tool_executors = {name: pg_executor for name in EXECUTORS}
        use_cases = build_use_cases(settings, tool_executors=tool_executors)
        _adapter = MCPServerAdapter(use_cases)
    return _adapter


# ── Tool definitions (delegated to the adapter / use case) ────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return await get_adapter().list_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return await get_adapter().call_tool(name, arguments)


# ── Resources ─────────────────────────────────────────────────────────────────

@server.list_resources()
async def list_resources() -> list[types.Resource]:
    items = await list_project_resources()
    return [
        types.Resource(uri=r["uri"], name=r["name"], description=r["description"], mimeType="application/json")
        for r in items
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri.startswith("project://"):
        return await read_project_resource(uri.removeprefix("project://"))
    if uri.startswith("artifact://"):
        return await read_artifact_resource(uri.removeprefix("artifact://"))
    return json.dumps({"error": f"Unknown resource URI: {uri}"})


# ── Entry points ──────────────────────────────────────────────────────────────

async def _main_stdio() -> None:
    await bootstrap(warmup_fn=get_adapter)
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
    await shutdown()


def resolve_serve_web_ui(flag: bool | None) -> bool:
    """Resolve static-UI serving: explicit flag wins, else the setting."""
    if flag is not None:
        return flag
    return bool(getattr(settings, "serve_web_ui", False))


def _default_web_dist() -> "Any":
    from pathlib import Path

    # .../mcp-server/src/opensddrag/mcp/server.py → repo root → web/dist
    return Path(__file__).resolve().parents[4] / "web" / "dist"


class _RewriteMcpPath:
    """Rewrite `/mcp` → `/mcp/` in-process (no HTTP redirect).

    Starlette's router 307s `/mcp` to `/mcp/` because `Mount("/mcp")`
    only matches `/mcp/...`. Streamable HTTP clients that follow the
    redirect drop `Authorization`, so the next hop looks like a bad API key.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") in ("http", "websocket") and scope.get("path") == "/mcp":
            scope = dict(scope)
            scope["path"] = "/mcp/"
            if scope.get("raw_path") == b"/mcp":
                scope["raw_path"] = b"/mcp/"
        await self.app(scope, receive, send)


def build_http_app(
    *,
    mcp_app: Any,
    serve_web_ui: bool,
    static_dir: Any | None = None,
    auth_enabled: bool | None = None,
) -> Any:
    """Assemble the SSE-mode Starlette app (mcp-server REQ-011/012/016).

    Routes, in priority order:
        1. `/mcp`  — MCP transport (wrapped in `AuthMiddleware` when enabled;
                     the middleware is scoped to this mount so the `/api/v1`
                     bearer gate is not double-applied).
        2. `/api/v1/...` — management REST routes.
        3. `/` (only when `serve_web_ui`) — static catch-all for `web/dist`.

    `/api/v1` and `/mcp` therefore always take precedence over the static
    mount. Kept separate from `_main_sse` so tests can build the app
    without starting uvicorn or bootstrapping the DB pool.
    """
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.routing import Mount
    from starlette.staticfiles import StaticFiles

    from opensddrag.infrastructure.management_service import build_management_service
    from opensddrag.mcp.auth import AuthMiddleware
    from opensddrag.web.deps import wire_cors
    from opensddrag.web.routes import build_routes

    use_auth = settings.auth_enabled if auth_enabled is None else auth_enabled
    mcp_endpoint: Any = AuthMiddleware(mcp_app) if use_auth else mcp_app

    routes: list[Any] = [
        Mount("/mcp", app=mcp_endpoint),
        *build_routes(build_management_service()),
    ]

    if serve_web_ui:
        from pathlib import Path as _Path

        directory = _Path(static_dir) if static_dir is not None else _default_web_dist()
        if directory.is_dir():
            routes.append(Mount("/", app=StaticFiles(directory=str(directory), html=True)))

    # Path rewrite must be outermost so POST /mcp never 307s. Cursor's
    # Streamable HTTP client follows that redirect without the configured
    # Bearer token and AuthMiddleware then returns 401 invalid/revoked key.
    return Starlette(
        routes=routes,
        middleware=[Middleware(_RewriteMcpPath), *wire_cors(settings)],
    )


async def _main_sse(host: str, port: int, serve_web_ui: bool | None = None) -> None:
    import logging
    import uvicorn
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    await bootstrap(warmup_fn=get_adapter)
    session_manager = StreamableHTTPSessionManager(app=server, event_store=None, json_response=False)

    class _MCPApp:
        async def __call__(self, scope, receive, send):
            await session_manager.handle_request(scope, receive, send)

    if not settings.auth_enabled:
        logging.warning("WARNING: Auth is disabled. Do not expose this server publicly.")

    app = build_http_app(
        mcp_app=_MCPApp(), serve_web_ui=resolve_serve_web_ui(serve_web_ui)
    )
    async with session_manager.run():
        await uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="info")).serve()
    await shutdown()


def run(transport: str = "stdio", host: str = "0.0.0.0", port: int = 8000, serve_web_ui: bool | None = None) -> None:
    if transport == "sse":
        asyncio.run(_main_sse(host, port, serve_web_ui))
    else:
        asyncio.run(_main_stdio())


def run_web(host: str = "0.0.0.0", port: int = 8000, serve_ui: bool | None = None) -> None:
    """Start the HTTP server with the management REST API (+ optional UI)."""
    asyncio.run(_main_sse(host, port, serve_web_ui=serve_ui))
