import asyncio

import typer
from rich.console import Console
from rich.table import Table

from opensddrag.cli._common import resolve_project_id
from opensddrag.db import repository
from opensddrag.embedding.service import embed
from opensddrag.models.artifact import ArtifactCreate, ArtifactType

app = typer.Typer(help="Manage change artifacts.")
console = Console()


@app.command("create")
def create(
    name: str = typer.Argument(...),
    project: str = typer.Option(None, "--project", "-p"),
):
    """Create a new change artifact."""
    async def _run():
        project_id, slug = await resolve_project_id(project)
        console.print(f"[bold]Creating change '{name}' in project '{slug}'[/bold]")
        console.print("[dim]Paste content. End with '.' on a new line:[/dim]")
        lines = []
        while True:
            line = input()
            if line == ".":
                break
            lines.append(line)
        content = "\n".join(lines)
        embedding = embed(content)
        data = ArtifactCreate(project_id=project_id, name=name, type=ArtifactType.change, content=content)
        artifact = await repository.create_artifact(data, embedding)
        console.print(f"[green]✓ Change '{artifact.name}' created.[/green]")
    asyncio.run(_run())


@app.command("list")
def list_changes(project: str = typer.Option(None, "--project", "-p")):
    """List changes."""
    async def _run():
        project_id, slug = await resolve_project_id(project)
        items = await repository.list_artifacts(project_id, ArtifactType.change)
        if not items:
            console.print(f"[yellow]No changes in project '{slug}'.[/yellow]")
            return
        table = Table("Name", "Status", "Updated")
        for i in items:
            table.add_row(i.name, i.status, str(i.updated_at.date()))
        console.print(table)
    asyncio.run(_run())
