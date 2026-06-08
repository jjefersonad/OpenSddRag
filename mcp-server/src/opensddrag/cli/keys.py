import asyncio
from datetime import datetime
from uuid import UUID

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from opensddrag.db import api_key_repository, project_repository

app = typer.Typer(help="Manage API keys for the MCP server.")
console = Console()


@app.command("create")
def create(
    project: str = typer.Option(None, "--project", "-p", help="Project slug to scope this key (omit for global)"),
    description: str = typer.Option("", "--description", "-d", help="Human-readable label for this key"),
    expires_at: str = typer.Option(None, "--expires-at", help="Expiry date in ISO format, e.g. '2026-12-31'"),
):
    """Create a new API key."""
    async def _run():
        project_id: UUID | None = None
        if project:
            proj = await project_repository.get_project_by_slug(project)
            if proj is None:
                console.print(f"[red]Project '{project}' not found.[/red]")
                raise typer.Exit(1)
            project_id = proj.id

        expires: datetime | None = None
        if expires_at:
            expires = datetime.fromisoformat(expires_at)

        key_record, plaintext = await api_key_repository.create_key(
            description=description,
            project_id=project_id,
            expires_at=expires,
        )

        scope = project or "(global)"
        console.print(Panel(
            f"[bold yellow]Save this key — it will not be shown again.[/bold yellow]\n\n"
            f"[bold green]{plaintext}[/bold green]\n\n"
            f"ID: {key_record.id}\n"
            f"Prefix: {key_record.key_prefix}\n"
            f"Scope: {scope}\n"
            f"Description: {key_record.description or '(none)'}",
            title="API Key Created",
            border_style="green",
        ))

    asyncio.run(_run())


@app.command("list")
def list_keys(
    project: str = typer.Option(None, "--project", "-p", help="Filter by project slug"),
):
    """List all API keys."""
    async def _run():
        project_id: UUID | None = None
        if project:
            proj = await project_repository.get_project_by_slug(project)
            if proj is None:
                console.print(f"[red]Project '{project}' not found.[/red]")
                raise typer.Exit(1)
            project_id = proj.id

        keys = await api_key_repository.list_keys(project_id=project_id)
        if not keys:
            console.print("[yellow]No API keys found.[/yellow]")
            return

        table = Table("ID", "Prefix", "Description", "Scope", "Created", "Expires", "Status")
        for k in keys:
            if k.revoked_at:
                status = "[red]revoked[/red]"
            elif k.expires_at and k.expires_at < datetime.now(k.expires_at.tzinfo):
                status = "[yellow]expired[/yellow]"
            else:
                status = "[green]active[/green]"
            table.add_row(
                str(k.id),
                k.key_prefix,
                k.description or "",
                str(k.project_id) if k.project_id else "global",
                str(k.created_at.date()),
                str(k.expires_at.date()) if k.expires_at else "",
                status,
            )
        console.print(table)

    asyncio.run(_run())


@app.command("revoke")
def revoke(
    key_id: str = typer.Argument(..., help="UUID of the key to revoke"),
):
    """Revoke an API key."""
    async def _run():
        try:
            uid = UUID(key_id)
        except ValueError:
            console.print(f"[red]Invalid key ID: {key_id}[/red]")
            raise typer.Exit(1)

        key = await api_key_repository.revoke_key(uid)
        if key is None:
            console.print(f"[red]Key not found: {key_id}[/red]")
            raise typer.Exit(1)

        if key.revoked_at:
            console.print(f"[yellow]Key {key_id[:8]}... was already revoked at {key.revoked_at}.[/yellow]")
        else:
            console.print(f"[green]✓ Key {key_id[:8]}... revoked.[/green]")

    asyncio.run(_run())
