import asyncio

import typer
from rich.console import Console
from rich.table import Table

from opensddrag.db import project_repository
from opensddrag.models.project import ProjectCreate

app = typer.Typer(help="Manage projects in the central database.")
console = Console()


@app.command("create")
def create(
    slug: str = typer.Argument(..., help="Short identifier, e.g. 'my-api'"),
    name: str = typer.Option(..., "--name", "-n", help="Display name"),
    description: str = typer.Option("", "--description", "-d"),
):
    """Create a new project."""
    async def _run():
        existing = await project_repository.get_project_by_slug(slug)
        if existing:
            console.print(f"[yellow]Project '{slug}' already exists.[/yellow]")
            return
        project = await project_repository.create_project(
            ProjectCreate(slug=slug, name=name, description=description or None)
        )
        console.print(f"[green]✓ Project '{project.slug}' created (id: {project.id})[/green]")
    asyncio.run(_run())


@app.command("list")
def list_projects():
    """List all projects."""
    async def _run():
        projects = await project_repository.list_projects()
        if not projects:
            console.print("[yellow]No projects found. Run: opensddrag project create <slug> --name 'Name'[/yellow]")
            return
        table = Table("Slug", "Name", "Description", "Created")
        for p in projects:
            table.add_row(p.slug, p.name, p.description or "", str(p.created_at.date()))
        console.print(table)
    asyncio.run(_run())


@app.command("show")
def show(slug: str):
    """Show project details."""
    async def _run():
        project = await project_repository.get_project_by_slug(slug)
        if not project:
            console.print(f"[red]Project '{slug}' not found.[/red]")
            raise typer.Exit(1)
        console.print(f"[bold]{project.name}[/bold] ({project.slug})")
        console.print(f"ID: {project.id}")
        console.print(f"Description: {project.description or '—'}")
        console.print(f"Created: {project.created_at}")
    asyncio.run(_run())
