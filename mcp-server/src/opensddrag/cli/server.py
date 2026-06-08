from enum import Enum

import typer
from rich.console import Console

app = typer.Typer(help="MCP server management.")
console = Console()


class Transport(str, Enum):
    stdio = "stdio"
    sse = "sse"


@app.command("start")
def start(
    transport: Transport = typer.Option(Transport.stdio, "--transport", "-t", help="stdio (local) or sse (HTTP/Docker)"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind (SSE only)"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on (SSE only)"),
):
    """Start the OpenSddRag MCP server.

    stdio: Claude Code spawns the process directly (local use).
    sse:   HTTP server — use when running in Docker or remotely.
    """
    from opensddrag.mcp.server import run

    if transport == Transport.sse:
        console.print(f"[dim]Starting OpenSddRag MCP server (SSE) on {host}:{port}...[/dim]")
    else:
        console.print("[dim]Starting OpenSddRag MCP server (stdio)...[/dim]")

    run(transport=transport.value, host=host, port=port)
