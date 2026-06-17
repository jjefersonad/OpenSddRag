import asyncio

import typer
from rich.console import Console

from opensddrag.cli._common import resolve_project_id
from opensddrag.db import repository
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
        # `query_text` is passed alongside `query_embedding` so the
        # repository can run the hybrid lexical+vector (RRF) pipeline
        # introduced by the `hybrid-search` capability of
        # `improve-retrieval-accuracy`. The CLI argument shape is unchanged;
        # `query` flows to the repository as the lexical source. The
        # repository falls back to the pure-vector path when
        # `settings.hybrid_search_enabled` is false.
        if all_projects:
            results = await repository.search_semantic(
                "*", embedding, limit, query_text=query
            )
        else:
            project_id, _ = await resolve_project_id(project)
            results = await repository.search_semantic(
                project_id, embedding, limit, query_text=query
            )
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return
        for a in results:
            console.print(f"\n[bold]{a.name}[/bold] [{a.type} · {a.status}]")
            console.print(a.content[:300] + ("…" if len(a.content) > 300 else ""))

    asyncio.run(_run())


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    """Show usage when no subcommand is given.

    The callback intentionally has no `Argument` or `Option`: the previous
    implementation accepted `query: str = typer.Argument(None)` here while
    the `artifacts` subcommand also accepted `query` as `Argument(...)`.
    Click/typer routed the positional value as a subcommand name, so
    `search "query"` failed with `No such command 'query'`. Removing every
    parameter from the callback eliminates that routing conflict.

    The subcommand stays a plain `def` and drives the async repository via
    `asyncio.run` (the same pattern as the other CLI modules); typer 0.26.7
    does not natively await `async def` commands, so an `async def` body here
    would silently never run.
    """
    if ctx.invoked_subcommand is None:
        console.print("Use: opensddrag-server search artifacts [OPTIONS] QUERY")
        console.print("Run 'opensddrag-server search --help' for details.")
