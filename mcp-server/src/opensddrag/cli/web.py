"""`opensddrag-server web` — integrated web UI + management REST server.

cli REQ-001/REQ-002 of `web-management-system`: a root-level command that
starts the SSE transport (MCP + /api/v1 management REST) and optionally
serves the built dashboard at `/`. The `--serve-ui/--no-serve-ui` flag
overrides the `SERVE_WEB_UI` setting.
"""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()


def web(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    serve_ui: bool | None = typer.Option(
        None,
        "--serve-ui/--no-serve-ui",
        help="Serve the built web UI at / (overrides SERVE_WEB_UI)",
    ),
):
    """Start the integrated web server (MCP + /api/v1 management REST + UI).

    Serves the MCP transport at /mcp, the management REST API at /api/v1,
    and — when enabled — the built dashboard (web/dist) at /.
    """
    from opensddrag.mcp.server import resolve_serve_web_ui, run_web

    effective = resolve_serve_web_ui(serve_ui)
    console.print(
        f"[dim]Starting OpenSddRag web server on {host}:{port} "
        f"(static UI {'enabled' if effective else 'disabled'})...[/dim]"
    )
    run_web(host=host, port=port, serve_ui=serve_ui)
