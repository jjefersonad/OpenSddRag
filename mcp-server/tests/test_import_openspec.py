"""Tests for opensddrag import openspec functionality."""

import os
from pathlib import Path
from uuid import uuid4

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://opensddrag:opensddrag@localhost:54326/opensddrag")
os.environ.setdefault("AUTH_ENABLED", "false")

from opensddrag.cli.import_openspec import import_openspec_path
from opensddrag.db import project_repository, repository
from opensddrag.models.artifact import ArtifactType
from opensddrag.models.project import ProjectCreate


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture()
def openspec_root(tmp_path: Path) -> Path:
    """Build a minimal OpenSpec project directory with one change and global specs."""
    root = tmp_path / "myproject"

    # Change artifacts
    change = root / "openspec" / "changes" / "add-auth"
    _write(change / "proposal.md", "## Why\n\nAdd authentication to the system.")
    _write(change / "design.md", "## Context\n\nTechnical design for auth.")
    _write(change / "tasks.md", "## 1. Core\n\n- [ ] 1.1 Implement login endpoint")
    _write(change / "specs" / "auth-login" / "spec.md", "## ADDED Requirements\n\n### Requirement: Login\nUsers SHALL log in.")

    # Global specs
    _write(root / "openspec" / "specs" / "user-profile" / "spec.md", "## ADDED Requirements\n\n### Requirement: Profile\nUsers SHALL have profiles.")

    return root


@pytest.fixture()
async def project_id(tmp_path: Path):
    """Create a unique test project and clean up its artifacts after the test."""
    slug = f"test-import-{uuid4().hex[:8]}"
    proj = await project_repository.create_project(ProjectCreate(slug=slug, name=slug))
    yield proj.id
    # Cleanup: delete all imported artifacts for this project
    artifacts = await repository.list_artifacts(proj.id)
    import psycopg
    from opensddrag.db.connection import get_conn
    async with get_conn() as conn:
        for a in artifacts:
            await conn.execute("DELETE FROM artifacts WHERE id = %s", (str(a.id),))
        await conn.execute("DELETE FROM projects WHERE id = %s", (str(proj.id),))


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_happy_path(openspec_root: Path, project_id):
    """All four artifact types are imported with correct type, embedding, source_path."""
    result = await import_openspec_path(openspec_root, project_id)

    assert result.failed == 0
    assert result.skipped == 0
    assert result.imported == 5  # proposal + design + tasks + spec (change) + spec (global)

    artifacts = await repository.list_artifacts(project_id)
    assert len(artifacts) == 5

    by_type = {}
    for a in artifacts:
        by_type.setdefault(a.type, []).append(a)

    assert len(by_type[ArtifactType.proposal]) == 1
    assert len(by_type[ArtifactType.design]) == 1
    assert len(by_type[ArtifactType.task]) == 1
    assert len(by_type[ArtifactType.spec]) == 2

    for a in artifacts:
        assert a.metadata.get("source") == "openspec"
        assert "source_path" in a.metadata


@pytest.mark.asyncio
async def test_artifact_names(openspec_root: Path, project_id):
    """Artifact names follow OpenSddRag naming convention."""
    await import_openspec_path(openspec_root, project_id)
    artifacts = await repository.list_artifacts(project_id)
    names = {a.name for a in artifacts}

    assert "add-auth-proposal" in names
    assert "add-auth-design" in names
    assert "add-auth-task" in names
    assert "add-auth-auth-login-spec" in names
    assert "user-profile-spec" in names


@pytest.mark.asyncio
async def test_idempotency(openspec_root: Path, project_id):
    """Running import twice skips all on the second run."""
    result1 = await import_openspec_path(openspec_root, project_id)
    assert result1.imported == 5
    assert result1.skipped == 0

    result2 = await import_openspec_path(openspec_root, project_id)
    assert result2.imported == 0
    assert result2.skipped == 5

    artifacts = await repository.list_artifacts(project_id)
    assert len(artifacts) == 5


@pytest.mark.asyncio
async def test_force_reimport(openspec_root: Path, project_id):
    """Force flag re-imports and updates existing artifacts."""
    result1 = await import_openspec_path(openspec_root, project_id)
    assert result1.imported == 5

    result2 = await import_openspec_path(openspec_root, project_id, force=True)
    assert result2.imported == 5
    assert result2.skipped == 0

    artifacts = await repository.list_artifacts(project_id)
    assert len(artifacts) == 5


@pytest.mark.asyncio
async def test_relationship_creation(openspec_root: Path, project_id):
    """task artifact has depends_on links to spec and design of the same change."""
    await import_openspec_path(openspec_root, project_id)

    task_artifact = await repository.get_artifact(project_id, "add-auth-task")
    assert task_artifact is not None

    relationships = await repository.get_relationships(task_artifact.id)
    related_names = {r["name"] for r in relationships}

    assert "add-auth-auth-login-spec" in related_names
    assert "add-auth-design" in related_names


@pytest.mark.asyncio
async def test_spec_depends_on_proposal(openspec_root: Path, project_id):
    """Spec artifact has a depends_on link to the change's proposal."""
    await import_openspec_path(openspec_root, project_id)

    spec_artifact = await repository.get_artifact(project_id, "add-auth-auth-login-spec")
    assert spec_artifact is not None

    relationships = await repository.get_relationships(spec_artifact.id)
    related_names = {r["name"] for r in relationships}
    assert "add-auth-proposal" in related_names


@pytest.mark.asyncio
async def test_global_specs_have_no_change_name(openspec_root: Path, project_id):
    """Global specs under openspec/specs/ are imported with change_name=None."""
    await import_openspec_path(openspec_root, project_id)

    global_spec = await repository.get_artifact(project_id, "user-profile-spec")
    assert global_spec is not None
    assert global_spec.metadata.get("change_name") is None
    assert global_spec.metadata.get("source") == "openspec"


@pytest.mark.asyncio
async def test_change_filter(openspec_root: Path, project_id):
    """--change flag imports only the named change, skipping global specs."""
    result = await import_openspec_path(openspec_root, project_id, change_name="add-auth")

    # 4 artifacts: proposal + design + tasks + change spec (no global spec)
    assert result.imported == 4
    assert result.failed == 0

    artifacts = await repository.list_artifacts(project_id)
    assert len(artifacts) == 4
    names = {a.name for a in artifacts}
    assert "user-profile-spec" not in names


@pytest.mark.asyncio
async def test_missing_path_raises(project_id):
    """Import on a non-existent path raises ValueError with a clear message."""
    with pytest.raises(ValueError, match="No 'openspec/' directory"):
        await import_openspec_path(Path("/nonexistent/path/abc123"), project_id)
