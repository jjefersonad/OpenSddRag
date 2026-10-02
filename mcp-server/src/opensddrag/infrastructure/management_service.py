"""Concrete management service backing the /api/v1 REST adapter.

Lives in `infrastructure/` because it is allowed to import `db/`
repositories and the `embedding/` service. The REST delivery adapter
(`web/`) depends only on the `ManagementServiceProtocol` declared in
`web/service.py`; the composition/mount layer injects this implementation,
keeping `web/` free of `opensddrag.db` imports (mcp-server REQ-011/REQ-015).

All outputs are JSON-serializable primitives (str/int/float/dict/list) so
routers can hand them straight to `JSONResponse`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from opensddrag.core.domain.artifact_validation import validate as validate_artifact_content
from opensddrag.core.domain.errors import (
    ManagementValidationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from opensddrag.core.domain.rule_constants import (
    VALID_RULE_CATEGORIES,
    VALID_RULE_SEVERITIES,
    VALID_RULE_TRIGGERS,
)
from opensddrag.db import project_repository, repository, rule_repository, trace_repository
from opensddrag.embedding.service import embed
from opensddrag.models.artifact import Artifact, ArtifactCreate, ArtifactStatus, ArtifactType, ArtifactUpdate
from opensddrag.models.project import Project, ProjectCreate
from opensddrag.models.rule import Rule, RuleCreate
from opensddrag.models.trace import ExecutionTrace

_SNIPPET_LEN = 160


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _project_out(project: Project) -> dict[str, Any]:
    return {
        "id": str(project.id),
        "name": project.name,
        "slug": project.slug,
        "description": project.description,
        "created_at": _iso(project.created_at),
        "updated_at": _iso(project.updated_at),
    }


def _artifact_summary(artifact: Artifact) -> dict[str, Any]:
    return {
        "id": str(artifact.id),
        "name": artifact.name,
        "type": artifact.type.value,
        "status": artifact.status.value,
        "metadata": artifact.metadata,
        "created_at": _iso(artifact.created_at),
        "updated_at": _iso(artifact.updated_at),
    }


def _artifact_full(artifact: Artifact) -> dict[str, Any]:
    return {
        **_artifact_summary(artifact),
        "content": artifact.content,
    }


def _rule_out(rule: Rule) -> dict[str, Any]:
    return {
        "id": str(rule.id),
        "name": rule.name,
        "trigger": rule.trigger,
        "category": rule.category,
        "severity": rule.severity,
        "instruction": rule.instruction,
        "enabled": rule.enabled,
    }


def _trace_out(trace: ExecutionTrace) -> dict[str, Any]:
    return {
        "id": str(trace.id),
        "action": trace.action,
        "query": trace.query,
        "result_summary": trace.result_summary,
        "artifact_id": str(trace.artifact_id) if trace.artifact_id else None,
        "session_id": str(trace.session_id) if trace.session_id else None,
        "created_at": _iso(trace.created_at),
    }


def _snippet(content: str) -> str:
    collapsed = " ".join((content or "").split())
    return collapsed[:_SNIPPET_LEN]


VALID_RELATIONSHIP_TYPES = ("implements", "depends_on", "relates_to")


class SqlManagementService:
    """PostgreSQL-backed implementation of `ManagementServiceProtocol`."""

    async def list_projects(self) -> list[dict[str, Any]]:
        projects = await project_repository.list_projects()
        return [_project_out(p) for p in projects]

    async def create_project(
        self, name: str, slug: str, description: str = ""
    ) -> dict[str, Any]:
        if await project_repository.get_project_by_slug(slug) is not None:
            raise ResourceConflictError(f"project slug {slug!r} already exists")
        project = await project_repository.create_project(
            ProjectCreate(slug=slug, name=name, description=description or None)
        )
        return _project_out(project)

    async def get_project(self, slug: str) -> dict[str, Any]:
        project = await project_repository.get_project_by_slug(slug)
        if project is None:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        artifacts = await repository.list_artifacts(project.id)
        summary: dict[str, int] = {}
        for artifact in artifacts:
            key = artifact.type.value
            summary[key] = summary.get(key, 0) + 1
        return {**_project_out(project), "summary": summary}

    async def list_artifacts(
        self, slug: str, type_filter: str | None = None
    ) -> list[dict[str, Any]]:
        project = await project_repository.get_project_by_slug(slug)
        if project is None:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        artifact_type: ArtifactType | None = None
        if type_filter:
            try:
                artifact_type = ArtifactType(type_filter)
            except ValueError as exc:
                valid = ", ".join(t.value for t in ArtifactType)
                raise ManagementValidationError(
                    f"unknown artifact type {type_filter!r}", details=[valid]
                ) from exc
        artifacts = await repository.list_artifacts(project.id, type=artifact_type)
        return [_artifact_summary(a) for a in artifacts]

    async def get_artifact(self, artifact_id: str) -> dict[str, Any]:
        try:
            aid = UUID(artifact_id)
        except ValueError as exc:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found") from exc
        artifact = await repository.get_artifact_by_id(aid)
        if artifact is None:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")
        return _artifact_full(artifact)

    async def get_validation(self, artifact_id: str) -> dict[str, Any]:
        """Structural validation of an artifact (artifact-management REQ-006)."""
        try:
            aid = UUID(artifact_id)
        except ValueError as exc:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found") from exc
        artifact = await repository.get_artifact_by_id(aid)
        if artifact is None:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")

        linked_tests = 0
        if artifact.type == ArtifactType.task:
            linked_tests = await repository.count_implements_test_targets(artifact.id)

        issues = validate_artifact_content(
            artifact.type.value,
            artifact.content,
            task_metadata=artifact.metadata,
            task_linked_test_count=linked_tests,
        )
        return {"valid": not issues, "issues": issues}

    async def get_relationships(self, artifact_id: str) -> list[dict[str, Any]]:
        """List an artifact's links (artifact-management REQ-005)."""
        try:
            aid = UUID(artifact_id)
        except ValueError as exc:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found") from exc
        artifact = await repository.get_artifact_by_id(aid)
        if artifact is None:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")
        rows = await repository.get_relationships(aid)
        return [
            {
                "relationship_type": row["relationship_type"],
                "id": str(row["id"]),
                "name": row["name"],
                "type": row["type"],
                "status": row["status"],
            }
            for row in rows
        ]

    async def list_rules(
        self, slug: str, enabled_all: bool = False
    ) -> list[dict[str, Any]]:
        project = await project_repository.get_project_by_slug(slug)
        if project is None:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        rules = await rule_repository.list_all(
            project.id, enabled_only=not enabled_all
        )
        return [_rule_out(r) for r in rules]

    async def list_traces(
        self, slug: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        project = await project_repository.get_project_by_slug(slug)
        if project is None:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        traces = await trace_repository.list_traces(project.id, limit=limit)
        return [_trace_out(t) for t in traces]

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        # web-management-system-fixes REQ-007: search over artifacts AND traces.
        query_embedding = embed(query)
        artifacts = await repository.search_semantic(
            "*", query_embedding, limit=limit, query_text=query
        )
        projects = await project_repository.list_projects()
        slug_by_id = {p.id: p.slug for p in projects}

        combined: list[dict[str, Any]] = []
        for artifact in artifacts:
            combined.append(
                {
                    "type": artifact.type.value,
                    "title": artifact.name,
                    "snippet": _snippet(artifact.content),
                    "project": slug_by_id.get(
                        artifact.project_id, str(artifact.project_id)
                    ),
                    "slug": artifact.name,
                }
            )
        for project in projects:
            traces = await trace_repository.recall(
                project.id, query_embedding, limit=limit
            )
            for trace in traces:
                combined.append(
                    {
                        "type": "trace",
                        "title": trace.action,
                        "snippet": _snippet(trace.result_summary or trace.query or ""),
                        "project": slug_by_id.get(project.id, project.slug),
                        "slug": str(trace.id),
                    }
                )

        combined = combined[:limit]
        # Relevance ordering comes from pgvector/RRF; the numeric score is a
        # rank proxy (the prototype's score is fake too).
        for rank, item in enumerate(combined):
            item["score"] = round(1.0 / (rank + 1), 6)
        return combined

    # ── Mutations (web-management-system backend-5) ──────────────────────────

    async def _project_or_404(self, slug: str) -> Project:
        project = await project_repository.get_project_by_slug(slug)
        if project is None:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        return project

    async def set_task_done(
        self, slug: str, task_id: str, done: bool
    ) -> dict[str, Any]:
        project = await self._project_or_404(slug)
        try:
            aid = UUID(task_id)
        except ValueError as exc:
            raise ResourceNotFoundError(f"task {task_id!r} not found") from exc
        task = await repository.get_artifact_by_id(aid)
        if task is None or task.project_id != project.id:
            raise ResourceNotFoundError(
                f"task {task_id!r} not found in project {slug!r}"
            )
        updated = await repository.update_artifact(
            project.id, task.name, ArtifactUpdate(metadata={"done": done})
        )
        if updated is None:
            raise ResourceNotFoundError(f"task {task_id!r} not found")
        return _artifact_full(updated)

    async def create_rule(
        self,
        slug: str,
        name: str,
        trigger: str,
        category: str,
        severity: str,
        instruction: str,
    ) -> dict[str, Any]:
        project = await self._project_or_404(slug)
        if trigger not in VALID_RULE_TRIGGERS:
            raise ManagementValidationError(
                f"invalid trigger {trigger!r}", details=list(VALID_RULE_TRIGGERS)
            )
        if category not in VALID_RULE_CATEGORIES:
            raise ManagementValidationError(
                f"invalid category {category!r}", details=list(VALID_RULE_CATEGORIES)
            )
        if severity not in VALID_RULE_SEVERITIES:
            raise ManagementValidationError(
                f"invalid severity {severity!r}", details=list(VALID_RULE_SEVERITIES)
            )
        rule = await rule_repository.upsert(
            RuleCreate(
                project_id=project.id,
                name=name,
                trigger=trigger,
                category=category,
                severity=severity,
                instruction=instruction,
                enabled=True,
            )
        )
        return _rule_out(rule)

    async def set_rule_enabled(
        self, slug: str, rule_id: str, enabled: bool
    ) -> dict[str, Any]:
        project = await self._project_or_404(slug)
        rules = await rule_repository.list_all(project.id, enabled_only=False)
        match = next((r for r in rules if str(r.id) == rule_id), None)
        if match is None:
            raise ResourceNotFoundError(f"rule {rule_id!r} not found")
        updated = await rule_repository.upsert(
            RuleCreate(
                project_id=project.id,
                name=match.name,
                trigger=match.trigger,
                category=match.category,
                severity=match.severity,
                instruction=match.instruction,
                enabled=enabled,
                metadata=match.metadata,
            )
        )
        return _rule_out(updated)

    async def create_artifact(
        self,
        slug: str,
        name: str,
        type_filter: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        project = await self._project_or_404(slug)
        try:
            artifact_type = ArtifactType(type_filter)
        except ValueError as exc:
            valid = ", ".join(t.value for t in ArtifactType)
            raise ManagementValidationError(
                f"unknown artifact type {type_filter!r}", details=[valid]
            ) from exc
        if await repository.get_artifact(project.id, name) is not None:
            raise ResourceConflictError(f"artifact name {name!r} already exists")
        embedding = embed(content)
        created = await repository.create_artifact(
            ArtifactCreate(
                project_id=project.id,
                name=name,
                type=artifact_type,
                content=content,
                status=ArtifactStatus.draft,
                metadata=metadata or {},
            ),
            embedding,
        )
        return _artifact_full(created)

    async def update_artifact(
        self,
        artifact_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        try:
            aid = UUID(artifact_id)
        except ValueError as exc:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found") from exc
        artifact = await repository.get_artifact_by_id(aid)
        if artifact is None:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")
        status_enum: ArtifactStatus | None = None
        if status is not None:
            try:
                status_enum = ArtifactStatus(status)
            except ValueError as exc:
                valid = ", ".join(s.value for s in ArtifactStatus)
                raise ManagementValidationError(
                    f"unknown status {status!r}", details=[valid]
                ) from exc
        embedding = embed(content) if content is not None else None
        updated = await repository.update_artifact(
            artifact.project_id,
            artifact.name,
            ArtifactUpdate(content=content, metadata=metadata, status=status_enum),
            embedding,
        )
        if updated is None:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")
        return _artifact_full(updated)

    async def link_artifact(
        self,
        artifact_id: str,
        relationship_type: str,
        target_name: str | None = None,
        target_id: str | None = None,
    ) -> dict[str, Any]:
        if relationship_type not in VALID_RELATIONSHIP_TYPES:
            raise ManagementValidationError(
                f"invalid relationship_type {relationship_type!r}",
                details=list(VALID_RELATIONSHIP_TYPES),
            )
        try:
            source_id = UUID(artifact_id)
        except ValueError as exc:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found") from exc
        source = await repository.get_artifact_by_id(source_id)
        if source is None:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")

        target: Artifact | None = None
        if target_id is not None:
            try:
                target = await repository.get_artifact_by_id(UUID(target_id))
            except ValueError:
                target = None
        elif target_name is not None:
            target = await repository.get_artifact(source.project_id, target_name)
        if target is None:
            raise ResourceNotFoundError("target artifact not found")

        relationship = await repository.link_artifacts(
            source.id, target.id, relationship_type
        )
        return {
            "id": str(relationship.id),
            "source_id": str(relationship.source_id),
            "target_id": str(relationship.target_id),
            "relationship_type": relationship.relationship_type,
            "created_at": _iso(relationship.created_at),
        }


def build_management_service() -> SqlManagementService:
    """Factory used by the composition/mount layer (backend-6)."""
    return SqlManagementService()


__all__ = ["SqlManagementService", "build_management_service"]