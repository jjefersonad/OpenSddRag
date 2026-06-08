import asyncio

import typer
from rich.console import Console
from rich.table import Table

from opensddrag.cli._common import resolve_project_id
from opensddrag.db import repository
from opensddrag.embedding.service import embed
from opensddrag.models.artifact import ArtifactCreate, ArtifactStatus, ArtifactType, ArtifactUpdate

app = typer.Typer(help="Manage task artifacts.")
console = Console()


@app.command("create")
def create(
    name: str = typer.Argument(...),
    project: str = typer.Option(None, "--project", "-p"),
):
    """Create a new task artifact."""
    async def _run():
        project_id, slug = await resolve_project_id(project)
        console.print(f"[bold]Creating task '{name}' in project '{slug}'[/bold]")
        console.print("[dim]Paste content. End with '.' on a new line:[/dim]")
        lines = []
        while True:
            line = input()
            if line == ".":
                break
            lines.append(line)
        content = "\n".join(lines)
        embedding = embed(content)
        data = ArtifactCreate(project_id=project_id, name=name, type=ArtifactType.task, content=content)
        artifact = await repository.create_artifact(data, embedding)
        console.print(f"[green]✓ Task '{artifact.name}' created.[/green]")
    asyncio.run(_run())


@app.command("list")
def list_tasks(project: str = typer.Option(None, "--project", "-p")):
    """List tasks."""
    async def _run():
        project_id, slug = await resolve_project_id(project)
        items = await repository.list_artifacts(project_id, ArtifactType.task)
        if not items:
            console.print(f"[yellow]No tasks in project '{slug}'.[/yellow]")
            return
        table = Table("Name", "Status", "Updated")
        for i in items:
            table.add_row(i.name, i.status, str(i.updated_at.date()))
        console.print(table)
    asyncio.run(_run())


@app.command("done")
def done(
    name: str = typer.Argument(...),
    project: str = typer.Option(None, "--project", "-p"),
):
    """Mark a task as archived (done)."""
    async def _run():
        project_id, _ = await resolve_project_id(project)
        artifact = await repository.update_artifact(
            project_id, name, ArtifactUpdate(status=ArtifactStatus.archived)
        )
        if not artifact:
            console.print(f"[red]Task '{name}' not found.[/red]")
            raise typer.Exit(1)
        console.print(f"[green]✓ Task '{name}' marked as done.[/green]")
    asyncio.run(_run())
