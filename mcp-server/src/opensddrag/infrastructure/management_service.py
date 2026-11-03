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

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from opensddrag.core.domain import change_progress
from opensddrag.core.domain.change_pages import paginate as paginate_changes
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
from opensddrag.db import (
    api_key_repository,
    project_repository,
    repository,
    rule_repository,
    session_repository,
    trace_repository,
)
from opensddrag.models.api_key import ApiKey
from opensddrag.db.flow_registry import registered_kinds
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
        "language": project.language,
        "created_at": _iso(project.created_at),
        "updated_at": _iso(project.updated_at),
    }


def _artifact_summary(artifact: Artifact, include_content: bool = False) -> dict[str, Any]:
    summary = {
        "id": str(artifact.id),
        "name": artifact.name,
        "type": artifact.type.value,
        "status": artifact.status.value,
        "flow": artifact.flow,
        "metadata": artifact.metadata,
        "created_at": _iso(artifact.created_at),
        "updated_at": _iso(artifact.updated_at),
    }
    if include_content:
        summary["content"] = artifact.content
    return summary


def _artifact_full(artifact: Artifact) -> dict[str, Any]:
    return _artifact_summary(artifact, include_content=True)


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


# ── Multi-flow helpers (web-ui-design-alignment D3/D6/D8) ────────────────────


# ── Change-tree helpers (web-artifact-hierarchy, web-api delta REQ-010) ──────

_DEPTH_BY_TYPE = {"proposal": 0, "spec": 1, "design": 1, "task": 2, "test": 3}


async def _change_tree(project_id: UUID) -> dict[str, Any]:
    """Build the active change's artifact tree (nodes + edges per flow).

    Active change = most recent non-archived `metadata.change_name` in the
    project. Depth is canonical per type (proposal 0, spec/design 1, task 2,
    test 3); edges come from `artifact_relationships` between the change's
    artifacts. Unlinked artifacts stay in the tree at their canonical depth
    (design D3 fallback).
    """
    import psycopg.rows
    from opensddrag.db.connection import get_conn as _gc

    artifacts = await repository.list_artifacts(project_id)
    live = [a for a in artifacts if a.status.value in ("draft", "active")]
    if not live:
        return {"change": None, "flows": []}

    # most recent non-archived change name
    active_change = next(
        (a.metadata.get("change_name") for a in live if a.metadata.get("change_name")),
        None,
    )
    # fall back to any non-archived change-named artifact's change_name with
    # the most recent created_at — list_artifacts orders by created_at desc,
    # so the first hit wins.
    if active_change is None:
        return {"change": None, "flows": []}

    members = [a for a in live if a.metadata.get("change_name") == active_change]
    ids = [a.id for a in members]
    id_set = set(str(i) for i in ids)
    by_id = {str(a.id): a for a in members}

    edges: list[dict[str, Any]] = []
    async with _gc() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT source_id, target_id, relationship_type
                FROM artifact_relationships
                WHERE source_id = ANY(%s::uuid[]) AND target_id = ANY(%s::uuid[])
                """,
                ([str(i) for i in ids], [str(i) for i in ids]),
            )
            for row in await cur.fetchall():
                edges.append(
                    {
                        "source": by_id[str(row["source_id"])]["flow"] if False else str(row["source_id"]),
                        "target": str(row["target_id"]),
                        "relationship_type": row["relationship_type"],
                    }
                )

    def _node(a: Artifact) -> dict[str, Any]:
        return {
            "id": str(a.id),
            "name": a.name,
            "type": a.type.value,
            "status": a.status.value,
            "depth": _DEPTH_BY_TYPE.get(a.type.value, 2),
            "flow": a.flow,
        }

    out_flows: dict[str, list[dict[str, Any]]] = {}
    for artifact in members:
        out_flows.setdefault(artifact.flow, []).append(_node(artifact))
    for flow in out_flows:
        out_flows[flow].sort(key=lambda n: (n["depth"], n["name"]))

    return {
        "change": active_change,
        "flows": [
            {"flow": flow, "nodes": nodes, "edges": edges}
            for flow, nodes in sorted(out_flows.items())
        ],
    }


async def _flow_registry_rows() -> list[tuple[str, str | None, Any]]:
    """(flow, manifest JSONB text, registered_at) for every registered flow."""
    from opensddrag.db.connection import get_conn
    import psycopg.rows

    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute("SELECT flow, manifest::text, registered_at FROM flows ORDER BY flow")
            return [(r["flow"], r["manifest"], r["registered_at"]) for r in await cur.fetchall()]


def _change_artifact(
    type_: str,
    status: str,
    flow: str,
    metadata: dict[str, Any],
    updated_at: Any,
) -> change_progress.ChangeArtifact:
    """Map persisted artifact fields to the pure-domain `ChangeArtifact`."""
    return change_progress.ChangeArtifact(
        type=type_,
        status=status,
        flow=flow,
        change_name=metadata.get("change_name") or None,
        is_delta=bool(metadata.get("is_delta")),
        done=bool(metadata.get("done")),
        updated_at=updated_at,
    )


def _from_artifact(artifact: Artifact) -> change_progress.ChangeArtifact:
    return _change_artifact(
        artifact.type.value,
        artifact.status.value,
        artifact.flow,
        artifact.metadata,
        artifact.updated_at,
    )


def _lifecycle_of(manifest_json: str | None) -> list[dict[str, Any]] | None:
    if not manifest_json:
        return None
    try:
        return json.loads(manifest_json).get("lifecycle") or None
    except (TypeError, ValueError, AttributeError):
        return None


async def _lifecycle_by_flow() -> dict[str, list[dict[str, Any]] | None]:
    """Declared lifecycle of every registered flow (None when it declares none)."""
    return {
        flow: _lifecycle_of(manifest_json)
        for flow, manifest_json, _registered_at in await _flow_registry_rows()
    }


def _aggregate_task_progress(per_flow: list[dict[str, Any]]) -> dict[str, int]:
    """Sum task_progress over flows (design D8 — dashboard card aggregate)."""
    done = sum(f["task_progress"]["done"] for f in per_flow)
    total = sum(f["task_progress"]["total"] for f in per_flow)
    return {"done": done, "total": total}


async def _per_flow_summaries(project_id: UUID) -> list[dict[str, Any]]:
    """Per-flow {flow, phase, task_progress} for the enriched project detail.

    Phase and progress come from `core.domain.change_progress` (live changes
    only, progress-based phase — project-management REQ-005/006/007), listed
    in registry order for flows that have artifacts in the project.
    """
    artifacts = [_from_artifact(a) for a in await repository.list_artifacts(project_id)]
    lifecycles = await _lifecycle_by_flow()
    by_flow = {s["flow"]: s for s in change_progress.flow_summaries(lifecycles, artifacts)}
    return [by_flow[flow] for flow in lifecycles if flow in by_flow]


VALID_RELATIONSHIP_TYPES = ("implements", "depends_on", "relates_to")


class SqlManagementService:
    """PostgreSQL-backed implementation of `ManagementServiceProtocol`."""

    async def list_projects(self) -> list[dict[str, Any]]:
        """Projects with stage, pipeline and progress (web-api REQ-012).

        One projects query + one lightweight artifact query for ALL projects
        + one flow-registry read, regardless of the project count (design D4).
        """
        projects = await project_repository.list_projects()
        rows = await repository.list_artifact_stubs([p.id for p in projects])
        by_project: dict[UUID, list[change_progress.ChangeArtifact]] = {}
        for row in rows:
            by_project.setdefault(row["project_id"], []).append(
                _change_artifact(
                    row["type"], row["status"], row["flow"], row["metadata"] or {}, row["updated_at"]
                )
            )
        lifecycles = await _lifecycle_by_flow()
        out: list[dict[str, Any]] = []
        for project in projects:
            summary = change_progress.project_summary(
                lifecycles, by_project.get(project.id, []), project.default_flow
            )
            out.append({**_project_out(project), **summary})
        return out

    async def create_project(
        self, name: str, slug: str, description: str = "", language: str = ""
    ) -> dict[str, Any]:
        if await project_repository.get_project_by_slug(slug) is not None:
            raise ResourceConflictError(f"project slug {slug!r} already exists")
        project = await project_repository.create_project(
            ProjectCreate(
                slug=slug, name=name, description=description or None, language=language
            )
        )
        return _project_out(project)

    async def update_project(
        self,
        slug: str,
        name: str | None = None,
        description: str | None = None,
        language: str | None = None,
        new_slug: str | None = None,
    ) -> dict[str, Any]:
        await self._project_or_404(slug)
        if new_slug and new_slug != slug:
            taken = await project_repository.get_project_by_slug(new_slug)
            if taken is not None:
                raise ResourceConflictError(f"project slug {new_slug!r} already exists")
        try:
            updated = await project_repository.update_project(
                slug,
                name=name,
                description=description,
                language=language,
                new_slug=new_slug,
            )
        except ValueError as exc:
            raise ResourceConflictError(str(exc)) from exc
        if updated is None:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        return _project_out(updated)

    async def delete_project(self, slug: str) -> dict[str, Any]:
        deleted = await project_repository.delete_project(slug)
        if not deleted:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        return {"deleted": True, "slug": slug}

    async def get_project(self, slug: str) -> dict[str, Any]:
        project = await project_repository.get_project_by_slug(slug)
        if project is None:
            raise ResourceNotFoundError(f"project {slug!r} not found")
        artifacts = await repository.list_artifacts(project.id)
        summary: dict[str, int] = {}
        for artifact in artifacts:
            key = artifact.type.value
            summary[key] = summary.get(key, 0) + 1
        per_flow = await _per_flow_summaries(project.id)
        return {
            **_project_out(project),
            "summary": summary,
            "flows": per_flow,
            "task_progress": _aggregate_task_progress(per_flow),
        }

    async def list_flows(self) -> list[dict[str, Any]]:
        """Registered flows with kinds + lifecycle (web-api delta REQ-008).

        Shape per flow: {flow, kinds: [{kind, rules}], lifecycle | null,
        harness_triggers, registered_at}. Lifecycle/manifest data comes from
        the stored `flows.manifest` JSONB; bare manifests (migration 008
        seed) expose `lifecycle: null`.
        """
        out: list[dict[str, Any]] = []
        for flow, manifest_json, registered_at in await _flow_registry_rows():
            kinds = await registered_kinds(flow)
            manifest: dict[str, Any] = {}
            if manifest_json:
                try:
                    manifest = json.loads(manifest_json)
                except (TypeError, ValueError):
                    manifest = {}
            out.append(
                {
                    "flow": flow,
                    "kinds": kinds,
                    "lifecycle": manifest.get("lifecycle"),
                    "harness_triggers": manifest.get("harness_triggers", []),
                    "registered_at": _iso(registered_at),
                }
            )
        return out

    async def get_session(self, slug: str) -> dict[str, Any]:
        """Working context summary (project delta, design D4)."""
        project = await self._project_or_404(slug)
        session = await session_repository.get_or_create(project.id)
        active: list[dict[str, Any]] = []
        for aid in session.active_artifact_ids:
            artifact = await repository.get_artifact_by_id(aid)
            if artifact is not None:
                active.append(
                    {"id": str(artifact.id), "name": artifact.name, "type": artifact.type.value}
                )
        return {
            "active_artifacts": active,
            "note": session.context.get("note") if isinstance(session.context, dict) else None,
        }

    async def get_tree(self, slug: str) -> dict[str, Any]:
        """Active-change artifact tree (web-artifact-hierarchy REQ-010)."""
        project = await self._project_or_404(slug)
        return await _change_tree(project.id)

    # SDD phase descriptions from the prototype (PHASES const).
    _PHASE_DESCS = {
        "Propose": "Define what & why — problem, changes, affected capabilities.",
        "Spec": "Testable requirements with WHEN/THEN scenarios.",
        "Design": "Technical decisions, trade-offs, risks.",
        "Tasks": "Break the design into trackable tasks.",
        "Apply": "Implement tasks, marking [ ] → [x].",
        "Verify": "Validate spec scenarios against the code.",
        "Sync": "Merge delta specs back into the base.",
        "Archive": "Close the change, record in history.",
    }

    async def list_changes(self, slug: str, page: int = 1, page_size: int = 8) -> dict[str, Any]:
        """One page of live changes, newest `updated_at` first (web-api REQ-011).

        Liveness, phase and task progress come from `core.domain.change_progress`
        (project-management REQ-005/006/007): synced main specs never keep a
        change live, phases are progress-based, archived tasks count as done.
        The page is applied after that derivation. `total` is the full count.
        """
        project = await self._project_or_404(slug)
        artifacts = await repository.list_artifacts(project.id)
        lifecycles = await _lifecycle_by_flow()
        live = change_progress.group_live_changes([_from_artifact(a) for a in artifacts])
        raw_by_name: dict[str, list[Artifact]] = {}
        for artifact in artifacts:
            change_name = (artifact.metadata or {}).get("change_name")
            if change_name:
                raw_by_name.setdefault(change_name, []).append(artifact)

        out: list[dict[str, Any]] = []
        for name, members in live.items():
            flow = members[0].flow
            phases = [
                {**phase, "desc": self._PHASE_DESCS.get(phase["name"], "Complete this phase's output.")}
                for phase in change_progress.derive_phases(lifecycles.get(flow), members)
            ]
            updated = max((m.updated_at for m in members if m.updated_at), default=None)
            raw = raw_by_name.get(name, [])
            started = min((m.created_at for m in raw if m.created_at), default=None)
            out.append(
                {
                    "change": name,
                    "flow": flow,
                    "started_at": _iso(started),
                    "updated_at": _iso(updated),
                    "task_progress": change_progress.task_progress(members),
                    "phases": phases,
                }
            )
        return paginate_changes(out, page, page_size)

    async def get_change_bundle(self, slug: str, change: str) -> dict[str, Any]:
        """Full-document bundle for one named change (web-api-management REQ-014).

        Membership matches MCP `read_change_bundle` (`metadata.change_name`),
        but tasks include `content` and a `done` flag so a human reader can
        see Goal/Steps. The MCP tool is intentionally left unchanged.
        """
        project = await self._project_or_404(slug)
        artifacts = await repository.list_artifacts(project.id)
        members = [a for a in artifacts if (a.metadata or {}).get("change_name") == change]
        if not members:
            raise ResourceNotFoundError(f"change {change!r} not found in project {slug!r}")

        def _first(kind: ArtifactType) -> dict[str, Any] | None:
            for artifact in members:
                if artifact.type == kind:
                    return _artifact_full(artifact)
            return None

        tasks: list[dict[str, Any]] = []
        for artifact in members:
            if artifact.type != ArtifactType.task:
                continue
            meta = artifact.metadata or {}
            tasks.append(
                {
                    "id": str(artifact.id),
                    "name": artifact.name,
                    "status": artifact.status.value,
                    "content": artifact.content,
                    "done": artifact.status.value == "archived" or bool(meta.get("done")),
                }
            )
        return {
            "change": change,
            "flow": members[0].flow,
            "proposal": _first(ArtifactType.proposal),
            "design": _first(ArtifactType.design),
            "specs": [_artifact_full(a) for a in members if a.type == ArtifactType.spec],
            "tasks": tasks,
            "task_count": len(tasks),
        }

    async def list_artifacts(
        self,
        slug: str,
        type_filter: str | None = None,
        flow_filter: str | None = None,
        include_content: bool = False,
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
        artifacts = await repository.list_artifacts(
            project.id, type=artifact_type, flow=flow_filter
        )
        return [_artifact_summary(a, include_content) for a in artifacts]

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
        name: str | None = None,
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
        if name is not None and name != artifact.name:
            taken = await repository.get_artifact(artifact.project_id, name)
            if taken is not None:
                raise ResourceConflictError(f"artifact name {name!r} already exists")
        embedding = embed(content) if content is not None else None
        updated = await repository.update_artifact(
            artifact.project_id,
            artifact.name,
            ArtifactUpdate(content=content, metadata=metadata, status=status_enum),
            embedding,
            new_name=name if name and name != artifact.name else None,
        )
        if updated is None:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")
        return _artifact_full(updated)

    async def delete_artifact(self, artifact_id: str) -> dict[str, Any]:
        try:
            aid = UUID(artifact_id)
        except ValueError as exc:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found") from exc
        deleted = await repository.delete_artifact(aid)
        if not deleted:
            raise ResourceNotFoundError(f"artifact {artifact_id!r} not found")
        return {"deleted": True, "id": artifact_id}

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

    async def list_api_keys(
        self,
        project_slug: str | None = None,
        include_revoked: bool = False,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        project_id = None
        global_only = False
        if scope not in (None, "", "global"):
            raise ManagementValidationError(
                f"invalid scope {scope!r}", details=["global"]
            )
        if scope == "global" and project_slug:
            raise ManagementValidationError(
                "scope=global cannot be combined with project"
            )
        if scope == "global":
            global_only = True
        elif project_slug:
            project_id = (await self._project_or_404(project_slug)).id
        keys = await api_key_repository.list_keys(
            project_id, include_revoked=include_revoked, global_only=global_only
        )
        slugs = await _project_slug_map()
        return [_api_key_out(key, slugs) for key in keys]

    async def create_api_key(
        self,
        description: str = "",
        project_slug: str | None = None,
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        project_id = None
        if project_slug:
            project_id = (await self._project_or_404(project_slug)).id
        key, plaintext = await api_key_repository.create_key(
            description=description,
            project_id=project_id,
            expires_at=_parse_expires_at(expires_at),
        )
        slugs = await _project_slug_map()
        return {**_api_key_out(key, slugs), "key": plaintext}

    async def revoke_api_key(self, key_id: str) -> dict[str, Any]:
        try:
            uid = UUID(key_id)
        except ValueError as exc:
            raise ResourceNotFoundError(f"api key {key_id!r} not found") from exc
        key = await api_key_repository.revoke_key(uid)
        if key is None:
            raise ResourceNotFoundError(f"api key {key_id!r} not found")
        slugs = await _project_slug_map()
        return _api_key_out(key, slugs)


def _parse_expires_at(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ManagementValidationError(
            "expires_at must be an ISO date or datetime"
        ) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _key_status(key: ApiKey) -> str:
    if key.revoked_at is not None:
        return "revoked"
    if key.expires_at is not None:
        expires = key.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(tz=timezone.utc):
            return "expired"
    return "active"


def _api_key_out(key: ApiKey, slugs: dict[UUID, str]) -> dict[str, Any]:
    return {
        "id": str(key.id),
        "prefix": key.key_prefix,
        "description": key.description,
        "project_slug": slugs.get(key.project_id) if key.project_id else None,
        "created_at": _iso(key.created_at),
        "expires_at": _iso(key.expires_at),
        "revoked_at": _iso(key.revoked_at),
        "status": _key_status(key),
    }


async def _project_slug_map() -> dict[UUID, str]:
    return {p.id: p.slug for p in await project_repository.list_projects()}


def build_management_service() -> SqlManagementService:
    """Factory used by the composition/mount layer (backend-6)."""
    return SqlManagementService()


__all__ = ["SqlManagementService", "build_management_service"]