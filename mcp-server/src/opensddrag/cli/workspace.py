"""opensddrag workspace init — run inside any project directory to connect it to OpenSddRag."""

import asyncio
import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from opensddrag.db import project_repository, skill_repository
from opensddrag.models.project import ProjectCreate

app = typer.Typer(help="Connect a project directory to the OpenSddRag Harness.")
console = Console()

_SKILL_MD = """\
# OpenSddRag — SDD + Harness

This project is connected to the OpenSddRag Harness. Use the MCP tools below to follow
Spec-Driven Development (SDD) with persistent memory and semantic search.

## When to use

Always check specs before implementing a feature:

```
search_semantic(query="<feature topic>", project_slug="{slug}")
```

Use the full SDD flow for any non-trivial change:

```
suggest_skill(objective="<your goal>", project_slug="{slug}")
```

## SDD Flow (Harness skills)

1. **sdd:propose** — write intent and scope before any code
2. **sdd:spec** — create spec with Purpose / Requirements / Scenarios
3. **sdd:design** — document technical decisions and trade-offs
4. **sdd:tasks** — decompose spec into atomic tasks (<4h each)
5. **sdd:apply** — implement each task against spec acceptance criteria
6. **sdd:full-flow** — run all steps above in sequence

## Key MCP tools

| Tool | When to use |
|------|-------------|
| `search_semantic` | Before implementing — find existing specs |
| `create_artifact` | To create proposal / spec / task / design |
| `read_artifact` | To read a specific spec or task |
| `list_artifacts` | To see all specs/tasks for this project |
| `suggest_skill` | To pick the right SDD workflow |
| `recall_episodes` | To recall what was done before in this project |
| `record_trace` | To log what you just did (episodic memory) |
| `get_working_context` | To see the active session |
| `update_working_context` | To set which artifacts are active now |
| `validate_artifact` | To check spec structure before saving |

## Project slug

Always pass `project_slug="{slug}"` to scope queries to this project.
Pass `project_slug="*"` to search across all projects.
"""

_CLAUDE_MD_BLOCK = """\

---

## OpenSddRag — SDD + Harness

This project uses OpenSddRag for Spec-Driven Development. The MCP server `opensddrag`
is configured and exposes semantic memory, episodic memory, skills, and SDD artifact tools.

**Project slug:** `{slug}`

Before implementing any feature:
1. Run `search_semantic` to find existing specs
2. Run `suggest_skill` to pick the right SDD workflow
3. Follow the skill steps to create proposal → spec → design → tasks

See `.claude/skills/opensddrag.md` for full tool reference.
"""


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except json.JSONDecodeError:
            existing = {}
        existing.update(data)
        data = existing
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _merge_mcp_server(settings_path: Path, server_name: str, server_config: dict) -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    except json.JSONDecodeError:
        existing = {}
    existing.setdefault("mcpServers", {})[server_name] = server_config
    settings_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n")


@app.command("init")
def init(
    slug: str = typer.Option(None, "--project", "-p", help="Project slug (default: current directory name)"),
    name: str = typer.Option(None, "--name", "-n", help="Project display name"),
    mcp_url: str = typer.Option(None, "--mcp-url", help="MCP server URL for SSE (e.g. http://localhost:8000/sse). Omit to use stdio."),
    mcp_command: str = typer.Option(None, "--mcp-command", help="MCP command for stdio (default: opensddrag server start)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
):
    """Initialize OpenSddRag in the current project directory.

    Run this command from inside the project you want to connect to OpenSddRag.
    It registers the project in the central database and sets up Claude Code integration.

    Examples:
        opensddrag workspace init
        opensddrag workspace init --project my-api --name "My API"
        opensddrag workspace init --mcp-url http://localhost:8000/sse
    """
    cwd = Path.cwd()

    # Resolve slug and name
    if not slug:
        slug = Prompt.ask("Project slug", default=cwd.name.lower().replace(" ", "-"))
    if not name:
        name = Prompt.ask("Project display name", default=slug.replace("-", " ").title())

    console.print(f"\n[bold]Initializing OpenSddRag in:[/bold] {cwd}")
    console.print(f"  Slug: [cyan]{slug}[/cyan]")
    console.print(f"  Name: [cyan]{name}[/cyan]")

    if mcp_url:
        console.print(f"  MCP:  [cyan]{mcp_url}[/cyan] (SSE)")
    else:
        cmd = mcp_command or "opensddrag server start"
        console.print(f"  MCP:  [cyan]{cmd}[/cyan] (stdio)")

    if not yes and not Confirm.ask("\nProceed?", default=True):
        raise typer.Exit()

    async def _run():
        # 1. Register project in central DB
        console.print("\n[bold green]1/4[/bold green] Registering project in database...")
        existing = await project_repository.get_project_by_slug(slug)
        if existing:
            console.print(f"  [yellow]Project '{slug}' already exists — skipping creation.[/yellow]")
            project = existing
        else:
            project = await project_repository.create_project(
                ProjectCreate(slug=slug, name=name)
            )
            console.print(f"  [green]✓ Project '{slug}' created (id: {project.id})[/green]")

        # 2. Write .claude/settings.json
        console.print("[bold green]2/4[/bold green] Configuring Claude Code MCP server...")
        settings_path = cwd / ".claude" / "settings.json"
        if mcp_url:
            server_cfg = {"url": mcp_url}
        else:
            server_cfg = {
                "command": (mcp_command or "opensddrag").split()[0],
                "args": (mcp_command or "opensddrag server start").split()[1:],
            }
        _merge_mcp_server(settings_path, "opensddrag", server_cfg)
        console.print(f"  [green]✓ {settings_path.relative_to(cwd)}[/green]")

        # 3. Write skill file
        console.print("[bold green]3/4[/bold green] Writing skill file...")
        skill_path = cwd / ".claude" / "skills" / "opensddrag.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(_SKILL_MD.format(slug=slug))
        console.print(f"  [green]✓ {skill_path.relative_to(cwd)}[/green]")

        # 4. Write/update CLAUDE.md
        console.print("[bold green]4/4[/bold green] Updating CLAUDE.md...")
        claude_md = cwd / "CLAUDE.md"
        block = _CLAUDE_MD_BLOCK.format(slug=slug)
        if claude_md.exists():
            content = claude_md.read_text()
            if "OpenSddRag" in content:
                console.print("  [yellow]CLAUDE.md already has OpenSddRag section — skipping.[/yellow]")
            else:
                claude_md.write_text(content.rstrip() + "\n" + block)
                console.print(f"  [green]✓ Appended OpenSddRag section to CLAUDE.md[/green]")
        else:
            claude_md.write_text(f"# {name}\n" + block)
            console.print(f"  [green]✓ Created CLAUDE.md[/green]")

        # 5. Write local opensddrag.yaml
        yaml_path = cwd / "opensddrag.yaml"
        if not yaml_path.exists():
            mcp_section = f"  url: {mcp_url}" if mcp_url else f"  command: {mcp_command or 'opensddrag server start'}"
            yaml_path.write_text(
                f"project: {slug}\n"
                f"mcp:\n{mcp_section}\n"
            )
            console.print(f"  [green]✓ Created opensddrag.yaml[/green]")

        console.print(f"\n[bold green]✓ Project '{slug}' connected to OpenSddRag![/bold green]")
        console.print("\nNext steps:")
        console.print(f"  [dim]opensddrag spec create --project {slug}[/dim]")
        console.print(f"  [dim]opensddrag search \"<topic>\" --project {slug}[/dim]")
        console.print("  Or open Claude Code — the MCP server is ready.")

    asyncio.run(_run())


@app.command("status")
def status():
    """Show the OpenSddRag connection status for the current directory."""
    cwd = Path.cwd()
    yaml_path = cwd / "opensddrag.yaml"
    settings_path = cwd / ".claude" / "settings.json"

    if yaml_path.exists():
        console.print(f"[green]✓[/green] {yaml_path.name} found")
        console.print(f"  {yaml_path.read_text().strip()}")
    else:
        console.print("[red]✗[/red] opensddrag.yaml not found — run: opensddrag workspace init")

    if settings_path.exists():
        try:
            cfg = json.loads(settings_path.read_text())
            mcp = cfg.get("mcpServers", {}).get("opensddrag")
            if mcp:
                console.print(f"[green]✓[/green] Claude Code MCP configured: {mcp}")
            else:
                console.print("[yellow]![/yellow] .claude/settings.json exists but 'opensddrag' MCP not found")
        except json.JSONDecodeError:
            console.print("[red]✗[/red] .claude/settings.json is invalid JSON")
    else:
        console.print("[yellow]![/yellow] .claude/settings.json not found")
