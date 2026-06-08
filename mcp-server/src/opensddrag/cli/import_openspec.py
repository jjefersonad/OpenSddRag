"""Import OpenSpec planning artifacts into OpenSddRag.

Walks an OpenSpec project directory and ingests all recognized artifact files
(proposal.md, design.md, tasks.md, specs/**/*.md) as typed, embedded artifacts
with `depends_on` relationships that mirror OpenSpec's dependency order.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from opensddrag.config import settings
from opensddrag.db import project_repository, repository
from opensddrag.embedding.service import embed
from opensddrag.models.artifact import Artifact, ArtifactCreate, ArtifactStatus, ArtifactType, ArtifactUpdate

app = typer.Typer(help="Import artifacts from external tools into OpenSddRag.")
console = Console()

# ─── File → ArtifactType mapping ──────────────────────────────────────────────

_FILENAME_TO_TYPE: dict[str, ArtifactType] = {
    "proposal.md": ArtifactType.proposal,
    "design.md": ArtifactType.design,
    "tasks.md": ArtifactType.task,
}


# ─── Discovery helpers ────────────────────────────────────────────────────────

@dataclass
class DiscoveredArtifact:
    file_path: Path
    artifact_type: ArtifactType
    name: str
    change_name: str | None


def _discover_change_artifacts(changes_dir: Path, change_name: str | None) -> list[DiscoveredArtifact]:
    """Walk openspec/changes/ and return all recognizable artifact files."""
    results: list[DiscoveredArtifact] = []
    if not changes_dir.is_dir():
        return results

    change_dirs = (
        [changes_dir / change_name]
        if change_name
        else [p for p in changes_dir.iterdir() if p.is_dir()]
    )

    for change_dir in change_dirs:
        if not change_dir.is_dir():
            continue
        cname = change_dir.name

        for fname, atype in _FILENAME_TO_TYPE.items():
            fpath = change_dir / fname
            if fpath.is_file():
                artifact_name = f"{cname}-{atype.value}"
                results.append(DiscoveredArtifact(fpath, atype, artifact_name, cname))

        specs_dir = change_dir / "specs"
        if specs_dir.is_dir():
            for spec_file in specs_dir.glob("**/*.md"):
                capability = spec_file.parent.name
                artifact_name = f"{cname}-{capability}-spec"
                results.append(DiscoveredArtifact(spec_file, ArtifactType.spec, artifact_name, cname))

    return results


def _discover_global_specs(specs_dir: Path) -> list[DiscoveredArtifact]:
    """Walk openspec/specs/ and return all global capability spec files."""
    results: list[DiscoveredArtifact] = []
    if not specs_dir.is_dir():
        return results

    for spec_file in specs_dir.glob("*/spec.md"):
        capability = spec_file.parent.name
        artifact_name = f"{capability}-spec"
        results.append(DiscoveredArtifact(spec_file, ArtifactType.spec, artifact_name, None))

    return results


# ─── Idempotency index ────────────────────────────────────────────────────────

async def _build_existing_index(project_id: UUID) -> dict[str, Artifact]:
    """Return {source_path: artifact} for all artifacts with metadata.source == 'openspec'."""
    all_artifacts = await repository.list_artifacts(project_id)
    return {
        a.metadata["source_path"]: a
        for a in all_artifacts
        if a.metadata.get("source") == "openspec" and "source_path" in a.metadata
    }


# ─── Core import function ─────────────────────────────────────────────────────

@dataclass
class ImportResult:
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    details: list[dict] = None

    def __post_init__(self):
        if self.details is None:
            self.details = []


async def import_openspec_path(
    root: Path,
    project_id: UUID,
    change_name: str | None = None,
    force: bool = False,
) -> ImportResult:
    """Discover and ingest OpenSpec artifacts from `root` into the database.

    Args:
        root: Path to the OpenSpec project root (contains an `openspec/` directory).
        project_id: Target OpenSddRag project UUID.
        change_name: Import only this change name; if None imports all changes.
        force: Re-import and re-embed even if artifact already exists.
    """
    openspec_dir = root / "openspec"
    if not openspec_dir.is_dir():
        raise ValueError(f"No 'openspec/' directory found at {root}")

    discovered = _discover_change_artifacts(openspec_dir / "changes", change_name)
    if change_name is None:
        discovered += _discover_global_specs(openspec_dir / "specs")

    if not discovered:
        return ImportResult()

    existing_index = await _build_existing_index(project_id)
    result = ImportResult()

    # First pass: upsert all artifacts
    upserted: dict[str, Artifact] = {}

    for item in discovered:
        rel_path = str(item.file_path.relative_to(root))
        try:
            content = item.file_path.read_text(encoding="utf-8")
            metadata = {
                "source": "openspec",
                "source_path": rel_path,
                "change_name": item.change_name,
            }

            if rel_path in existing_index and not force:
                upserted[rel_path] = existing_index[rel_path]
                result.skipped += 1
                result.details.append({"name": item.name, "status": "skipped", "path": rel_path})
                continue

            embedding = embed(content)

            if rel_path in existing_index:
                artifact = await repository.update_artifact(
                    project_id,
                    existing_index[rel_path].name,
                    ArtifactUpdate(content=content, metadata=metadata),
                    embedding=embedding,
                )
            else:
                artifact = await repository.create_artifact(
                    ArtifactCreate(
                        project_id=project_id,
                        name=item.name,
                        type=item.artifact_type,
                        content=content,
                        status=ArtifactStatus.active,
                        metadata=metadata,
                    ),
                    embedding,
                )

            upserted[rel_path] = artifact
            result.imported += 1
            result.details.append({"name": item.name, "status": "imported", "path": rel_path})

        except Exception as exc:
            result.failed += 1
            result.details.append({"name": item.name, "status": "failed", "path": rel_path, "error": str(exc)})

    # Second pass: create depends_on relationships per change
    await _create_relationships(discovered, upserted, root)

    return result


async def _create_relationships(
    discovered: list[DiscoveredArtifact],
    upserted: dict[str, Artifact],
    root: Path,
) -> None:
    """Create depends_on links mirroring OpenSpec's dependency order."""
    # Group artifacts by change_name
    by_change: dict[str | None, dict[ArtifactType, list[Artifact]]] = {}
    for item in discovered:
        rel_path = str(item.file_path.relative_to(root))
        artifact = upserted.get(rel_path)
        if artifact is None:
            continue
        by_change.setdefault(item.change_name, {}).setdefault(item.artifact_type, []).append(artifact)

    for _change_name, type_map in by_change.items():
        proposals = type_map.get(ArtifactType.proposal, [])
        designs = type_map.get(ArtifactType.design, [])
        specs = type_map.get(ArtifactType.spec, [])
        tasks = type_map.get(ArtifactType.task, [])

        proposal = proposals[0] if proposals else None
        design = designs[0] if designs else None

        for spec in specs:
            if proposal:
                await repository.link_artifacts(spec.id, proposal.id, "depends_on")

        if design and proposal:
            await repository.link_artifacts(design.id, proposal.id, "depends_on")

        for task in tasks:
            for spec in specs:
                await repository.link_artifacts(task.id, spec.id, "depends_on")
            if design:
                await repository.link_artifacts(task.id, design.id, "depends_on")


# ─── CLI command ──────────────────────────────────────────────────────────────

@app.command("openspec")
def import_openspec(
    path: str = typer.Argument(..., help="Path to the OpenSpec project root directory"),
    change: str | None = typer.Option(None, "--change", "-c", help="Import only this change name"),
    project: str | None = typer.Option(None, "--project", "-p", help="OpenSddRag project slug"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-import and re-embed existing artifacts"),
):
    """Import OpenSpec planning documents into OpenSddRag as searchable artifacts."""

    async def _run():
        root = Path(path).resolve()
        if not root.exists():
            console.print(f"[bold red]Error:[/bold red] Path does not exist: {root}")
            raise typer.Exit(1)

        slug = project or settings.opensddrag_project
        proj = await project_repository.require_project(slug)

        console.print(f"[bold]Importing OpenSpec artifacts[/bold] from [cyan]{root}[/cyan]")
        console.print(f"Project: [cyan]{slug}[/cyan]" + (f"  Change: [cyan]{change}[/cyan]" if change else ""))

        result = await import_openspec_path(root, proj.id, change_name=change, force=force)

        table = Table(title="Import Results", show_header=True)
        table.add_column("Artifact", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Path", style="dim")
        for d in result.details:
            status_style = {"imported": "green", "skipped": "yellow", "failed": "red"}.get(d["status"], "white")
            error = f"  [red]{d.get('error', '')}[/red]" if d["status"] == "failed" else ""
            table.add_row(d["name"], f"[{status_style}]{d['status']}[/{status_style}]{error}", d["path"])
        console.print(table)

        console.print(
            f"\n[bold green]✓[/bold green] Imported: [bold]{result.imported}[/bold]  "
            f"[yellow]Skipped: {result.skipped}[/yellow]  "
            f"[red]Failed: {result.failed}[/red]"
        )

    asyncio.run(_run())
