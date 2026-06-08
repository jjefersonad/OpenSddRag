import typer
from rich.console import Console

from opensddrag.cli import change, import_openspec, keys, project, search, server, session, skill, spec, task, workspace

app = typer.Typer(name="opensddrag", help="OpenSddRag — SDD + Harness with PostgreSQL/pgvector and MCP")
console = Console()

app.add_typer(project.app, name="project")
app.add_typer(spec.app, name="spec")
app.add_typer(change.app, name="change")
app.add_typer(task.app, name="task")
app.add_typer(skill.app, name="skill")
app.add_typer(search.app, name="search")
app.add_typer(session.app, name="session")
app.add_typer(server.app, name="server")
app.add_typer(workspace.app, name="workspace")
app.add_typer(keys.app, name="key")
app.add_typer(import_openspec.app, name="import")


@app.command()
def init():
    """Initialize database schema and seed global SDD skills."""
    import asyncio
    from opensddrag.db.connection import run_migrations
    from opensddrag.cli._seeds import seed_sdd_skills

    async def _run():
        console.print("[bold green]Running migrations...[/bold green]")
        await run_migrations()
        console.print("[bold green]Seeding global SDD skills...[/bold green]")
        await seed_sdd_skills()
        console.print("[bold green]✓ OpenSddRag initialized successfully.[/bold green]")

    asyncio.run(_run())


@app.command()
def migrate():
    """Apply pending database migrations."""
    import asyncio
    from opensddrag.db.connection import run_migrations

    async def _run():
        console.print("[bold green]Running migrations...[/bold green]")
        await run_migrations()
        console.print("[bold green]✓ Migrations applied.[/bold green]")

    asyncio.run(_run())
