import asyncio

import typer
from rich.console import Console

from opensddrag.cli._common import resolve_project_id
from opensddrag.db import session_repository

app = typer.Typer(help="Manage working context session.")
console = Console()


@app.command("show")
def show(project: str = typer.Option(None, "--project", "-p")):
    """Show current working session context."""
    async def _run():
        project_id, slug = await resolve_project_id(project)
        session = await session_repository.get_or_create(project_id)
        console.print(f"[bold]Session[/bold] {session.id} — project '{slug}'")
        console.print(f"Active artifact IDs: {session.active_artifact_ids or '(none)'}")
        console.print(f"Context: {session.context}")
        console.print(f"Started: {session.started_at}")
    asyncio.run(_run())
