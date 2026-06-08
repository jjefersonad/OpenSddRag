import asyncio

import typer
from rich.console import Console
from rich.table import Table

from opensddrag.cli._common import resolve_project_id
from opensddrag.db import skill_repository
from opensddrag.embedding.service import embed

app = typer.Typer(help="Manage SDD skills.")
console = Console()


@app.command("list")
def list_skills(project: str = typer.Option(None, "--project", "-p")):
    """List available skills (global + project-specific)."""
    async def _run():
        project_id, _ = await resolve_project_id(project)
        skills = await skill_repository.list_skills(project_id)
        if not skills:
            console.print("[yellow]No skills found.[/yellow]")
            return
        table = Table("Name", "Description", "Scope")
        for s in skills:
            scope = "[dim]global[/dim]" if s.project_id is None else "project"
            table.add_row(s.name, s.description, scope)
        console.print(table)
    asyncio.run(_run())


@app.command("show")
def show(name: str, project: str = typer.Option(None, "--project", "-p")):
    """Show a skill's workflow steps."""
    async def _run():
        project_id, _ = await resolve_project_id(project)
        skill = await skill_repository.get_skill(name, project_id)
        if not skill:
            console.print(f"[red]Skill '{name}' not found.[/red]")
            raise typer.Exit(1)
        console.print(f"[bold]{skill.name}[/bold] — {skill.description}")
        for step in skill.workflow_steps:
            required = "" if step.required else " [dim](optional)[/dim]"
            console.print(f"  {step.step}. {step.instruction}{required}")
    asyncio.run(_run())


@app.command("suggest")
def suggest(
    objective: str = typer.Argument(...),
    project: str = typer.Option(None, "--project", "-p"),
):
    """Suggest skills for a given objective using semantic search."""
    async def _run():
        project_id, _ = await resolve_project_id(project)
        embedding = embed(objective)
        skills = await skill_repository.suggest(project_id, embedding)
        if not skills:
            console.print("[yellow]No matching skills found.[/yellow]")
            return
        for s in skills:
            console.print(f"  [bold]{s.name}[/bold] — {s.description}")
    asyncio.run(_run())
