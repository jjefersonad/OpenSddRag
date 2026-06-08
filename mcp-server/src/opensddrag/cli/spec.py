import asyncio

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from opensddrag.cli._common import resolve_project_id
from opensddrag.db import repository
from opensddrag.embedding.service import embed
from opensddrag.models.artifact import ArtifactCreate, ArtifactType

app = typer.Typer(help="Manage spec artifacts.")
console = Console()

_TEMPLATE = """# Purpose

Describe the purpose of this spec.

# Requirements

- **REQ-001:** The system SHALL ...

# Scenarios

## Scenario 1: Happy path
...
"""


@app.command("create")
def create(
    name: str = typer.Argument(..., help="Spec name, e.g. 'auth-login'"),
    project: str = typer.Option(None, "--project", "-p"),
):
    """Create a new spec interactively."""
    async def _run():
        project_id, slug = await resolve_project_id(project)
        existing = await repository.get_artifact(project_id, name)
        if existing:
            console.print(f"[yellow]Spec '{name}' already exists in project '{slug}'.[/yellow]")
            return
        console.print(f"[bold]Creating spec '{name}' in project '{slug}'[/bold]")
        console.print("[dim]Paste your spec content below. End with a single '.' on a new line:[/dim]")
        lines = []
        while True:
            line = input()
            if line == ".":
                break
            lines.append(line)
        content = "\n".join(lines) if lines else _TEMPLATE
        embedding = embed(content)
        data = ArtifactCreate(project_id=project_id, name=name, type=ArtifactType.spec, content=content)
        artifact = await repository.create_artifact(data, embedding)
        console.print(f"[green]✓ Spec '{artifact.name}' created (id: {artifact.id})[/green]")
    asyncio.run(_run())


@app.command("list")
def list_specs(
    project: str = typer.Option(None, "--project", "-p"),
    all_projects: bool = typer.Option(False, "--all", help="List specs from all projects"),
):
    """List specs."""
    async def _run():
        if all_projects:
            from opensddrag.db import project_repository
            projects = await project_repository.list_projects()
            for proj in projects:
                specs = await repository.list_artifacts(proj.id, ArtifactType.spec)
                if specs:
                    console.print(f"\n[bold]{proj.name}[/bold] ({proj.slug})")
                    table = Table("Name", "Status", "Updated")
                    for s in specs:
                        table.add_row(s.name, s.status, str(s.updated_at.date()))
                    console.print(table)
        else:
            project_id, slug = await resolve_project_id(project)
            specs = await repository.list_artifacts(project_id, ArtifactType.spec)
            if not specs:
                console.print(f"[yellow]No specs in project '{slug}'.[/yellow]")
                return
            table = Table("Name", "Status", "Updated")
            for s in specs:
                table.add_row(s.name, s.status, str(s.updated_at.date()))
            console.print(table)
    asyncio.run(_run())


@app.command("view")
def view(
    name: str,
    project: str = typer.Option(None, "--project", "-p"),
):
    """View a spec's content."""
    async def _run():
        project_id, _ = await resolve_project_id(project)
        artifact = await repository.get_artifact(project_id, name)
        if not artifact:
            console.print(f"[red]Spec '{name}' not found.[/red]")
            raise typer.Exit(1)
        console.print(Markdown(artifact.content))
    asyncio.run(_run())
