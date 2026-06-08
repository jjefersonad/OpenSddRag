import asyncio

import typer
from rich.console import Console

from opensddrag.cli._common import resolve_project_id
from opensddrag.db import repository, trace_repository
from opensddrag.embedding.service import embed

app = typer.Typer(help="Search artifacts and episodic traces.")
console = Console()


@app.command("artifacts")
def search_artifacts(
    query: str = typer.Argument(...),
    project: str = typer.Option(None, "--project", "-p"),
    all_projects: bool = typer.Option(False, "--all", help="Search across all projects"),
    limit: int = typer.Option(5, "--limit", "-n"),
):
    """Semantic search over SDD artifacts."""
    async def _run():
        embedding = embed(query)
        if all_projects:
            results = await repository.search_semantic("*", embedding, limit)
        else:
            project_id, _ = await resolve_project_id(project)
            results = await repository.search_semantic(project_id, embedding, limit)
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return
        for a in results:
            console.print(f"\n[bold]{a.name}[/bold] [{a.type} · {a.status}]")
            console.print(a.content[:300] + ("…" if len(a.content) > 300 else ""))
    asyncio.run(_run())


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    query: str = typer.Argument(None),
    project: str = typer.Option(None, "--project", "-p"),
    all_projects: bool = typer.Option(False, "--all"),
    limit: int = typer.Option(5, "--limit", "-n"),
):
    """Semantic search (shorthand for 'search artifacts')."""
    if ctx.invoked_subcommand is None and query:
        search_artifacts(query, project, all_projects, limit)
