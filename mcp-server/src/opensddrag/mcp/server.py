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

    def _resolve_caller(self, request_or_scope: Any = None) -> Caller:
        if request_or_scope is not None:
            project_slug = getattr(
                getattr(request_or_scope, "state", None), "project_slug", None
            )
            caller_id = project_slug or "http"
            return Caller(caller_id=caller_id, permission=Permission.ADMIN)
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


async def _main_sse(host: str, port: int) -> None:
    import logging
    import uvicorn
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.routing import Mount
    from opensddrag.mcp.auth import AuthMiddleware

    await bootstrap(warmup_fn=get_adapter)
    session_manager = StreamableHTTPSessionManager(app=server, event_store=None, json_response=False)

    class _MCPApp:
        async def __call__(self, scope, receive, send):
            await session_manager.handle_request(scope, receive, send)

    if settings.auth_enabled:
        middleware = [Middleware(AuthMiddleware)]
    else:
        logging.warning("WARNING: Auth is disabled. Do not expose this server publicly.")
        middleware = []
    app = Starlette(routes=[Mount("/mcp", app=_MCPApp())], middleware=middleware)
    async with session_manager.run():
        await uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="info")).serve()
    await shutdown()


def run(transport: str = "stdio", host: str = "0.0.0.0", port: int = 8000) -> None:
    if transport == "sse":
        asyncio.run(_main_sse(host, port))
    else:
        asyncio.run(_main_stdio())
