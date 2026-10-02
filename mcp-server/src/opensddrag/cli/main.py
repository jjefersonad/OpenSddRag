import typer
from rich.console import Console

from opensddrag.cli import change, import_openspec, keys, project, search, server, session, skill, spec, task, workspace
from opensddrag.cli.web import web as web_command

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

# Root-level command: `opensddrag-server web` (cli REQ-001/REQ-002).
app.command(name="web")(web_command)


@app.command()
def init():
    """Initialize database schema, seed global SDD skills and harness rules."""
    import asyncio
    from opensddrag.db.connection import run_migrations
    from opensddrag.cli._seeds import seed_global_harness_rules, seed_sdd_skills
    from opensddrag.core.domain.flow_registry import ensure_sdd_flow

    async def _run():
        console.print("[bold green]Running migrations...[/bold green]")
        await run_migrations()
        console.print("[bold green]Seeding the sdd flow registry...[/bold green]")
        await ensure_sdd_flow()
        console.print("[bold green]Seeding global SDD skills...[/bold green]")
        await seed_sdd_skills()
        console.print("[bold green]Seeding global harness rules...[/bold green]")
        await seed_global_harness_rules()
        console.print("[bold green]✓ OpenSddRag initialized successfully.[/bold green]")

    asyncio.run(_run())


@app.command()
def register_flow(manifest_path: str):
    """Register a flow from its manifest JSON file (flow-registry REQ-002)."""
    import asyncio
    import json as _json
    import pathlib

    from opensddrag.core.domain.flow_manifest import ManifestValidationError
    from opensddrag.core.domain.flow_registry import register_flow

    async def _run():
        path = pathlib.Path(manifest_path)
        if not path.is_file():
            console.print(f"[bold red]✗ Manifest file not found: {manifest_path}[/bold red]")
            raise typer.Exit(code=1)
        try:
            payload = _json.loads(path.read_text())
        except _json.JSONDecodeError as exc:
            console.print(f"[bold red]✗ Manifest is not valid JSON: {exc}[/bold red]")
            raise typer.Exit(code=1)
        try:
            result = await register_flow(payload)
        except ManifestValidationError as exc:
            for issue in exc.issues:
                console.print(f"[bold red]✗ {issue}[/bold red]")
            raise typer.Exit(code=1)
        console.print(
            f"[bold green]✓ Flow '{result['flow']}' {result['status']} "
            f"({result['kinds']} kinds).[/bold green]"
        )

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
