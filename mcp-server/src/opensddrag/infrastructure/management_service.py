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
from opensddrag.db import project_repository, repository, rule_repository, session_repository, trace_repository
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


def _artifact_summary(artifact: Artifact) -> dict[str, Any]:
    return {
        "id": str(artifact.id),
        "name": artifact.name,
        "type": artifact.type.value,
        "status": artifact.status.value,
        "flow": artifact.flow,
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


def _derived_phase(
    lifecycle: list[dict[str, Any]] | None,
    artifacts: list[Artifact],
) -> str | None:
    """Derive the current phase of a flow (project delta REQ-005, design D6).

    The active phase is the first declared whose kinds still have a
    non-archived artifact; when every artifact is archived (or none exist
    but the flow is complete) the phase is the last declared one. A flow
    without a declared lifecycle derives `None` — the UI omits its strip.
    """
    if not lifecycle:
        return None
    kind_to_phase: dict[str, str] = {}
    for phase in lifecycle:
        for kind in phase.get("kinds", []):
            kind_to_phase.setdefault(kind, phase["name"])
    phase_names = [p["name"] for p in lifecycle]

    flow_artifacts = [a for a in artifacts if a.type.value in kind_to_phase]
    if not flow_artifacts:
        return phase_names[0]
    if all(a.status.value == "archived" for a in flow_artifacts):
        return phase_names[-1]
    for phase in lifecycle:
        kinds_in_phase = set(phase.get("kinds", []))
        has_open = any(
            a.type.value in kinds_in_phase and a.status.value != "archived"
            for a in flow_artifacts
        )
        if has_open:
            return phase["name"]
    return phase_names[-1]


def _aggregate_task_progress(per_flow: list[dict[str, Any]]) -> dict[str, int]:
    """Sum task_progress over flows (design D8 — dashboard card aggregate)."""
    done = sum(f["task_progress"]["done"] for f in per_flow)
    total = sum(f["task_progress"]["total"] for f in per_flow)
    return {"done": done, "total": total}


async def _per_flow_summaries(project_id: UUID) -> list[dict[str, Any]]:
    """Per-flow {flow, phase, task_progress} for the enriched project detail.

    Groups the project's artifacts by `flow`, derives each flow's phase
    from its declared lifecycle (REQ-005) and counts task done/total from
    artifact metadata.
    """
    artifacts = await repository.list_artifacts(project_id)
    by_flow: dict[str, list[Artifact]] = {}
    for artifact in artifacts:
        by_flow.setdefault(artifact.flow, []).append(artifact)

    summaries: list[dict[str, Any]] = []
    for flow, manifest_json, _registered_at in await _flow_registry_rows():
        flow_artifacts = by_flow.get(flow)
        if not flow_artifacts:
            continue
        lifecycle: list[dict[str, Any]] | None = None
        if manifest_json:
            try:
                stored = json.loads(manifest_json)
                lifecycle = stored.get("lifecycle") or None
            except (TypeError, ValueError):
                lifecycle = None
        tasks = [a for a in flow_artifacts if a.type.value == "task"]
        done = sum(1 for t in tasks if t.metadata.get("done"))
        summaries.append(
            {
                "flow": flow,
                "phase": _derived_phase(lifecycle, flow_artifacts),
                "task_progress": {"done": done, "total": len(tasks)},
            }
        )
    return summaries


VALID_RELATIONSHIP_TYPES = ("implements", "depends_on", "relates_to")


class SqlManagementService:
    """PostgreSQL-backed implementation of `ManagementServiceProtocol`."""

    async def list_projects(self) -> list[dict[str, Any]]:
        projects = await project_repository.list_projects()
        return [_project_out(p) for p in projects]

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

    async def list_changes(self, slug: str) -> list[dict[str, Any]]:
        """Changes in progress with per-change pipelines (REQ-011)."""
        from opensddrag.db.connection import get_conn as _gc
        import psycopg.rows

        project = await self._project_or_404(slug)
        artifacts = await repository.list_artifacts(project.id)
        # Changes-in-progress include their archived (done) artifacts — the
        # phase derivation needs the full chain to mark early phases `done`.
        # A change is "live" when it has at least one non-archived artifact.
        live_changes: dict[str, list[Artifact]] = {}
        for a in artifacts:
            chg = a.metadata.get("change_name")
            if chg:
                live_changes.setdefault(chg, []).append(a)
        changes = {
            chg: arts
            for chg, arts in live_changes.items()
            if any(a.status.value in ("draft", "active") for a in arts)
        }

        # one lifecycle lookup per flow needed (lazily)
        lifecycle_cache: dict[str, list[dict[str, Any]] | None] = {}

        async def _lifecycle(flow: str) -> list[dict[str, Any]] | None:
            if flow in lifecycle_cache:
                return lifecycle_cache[flow]
            for f, manifest_json, _r in await _flow_registry_rows():
                if f == flow:
                    manifest: dict[str, Any] = {}
                    if manifest_json:
                        try:
                            manifest = json.loads(manifest_json)
                        except (TypeError, ValueError):
                            manifest = {}
                    lifecycle_cache[flow] = manifest.get("lifecycle") or None
                    return lifecycle_cache[flow]
            lifecycle_cache[flow] = None
            return None

        out: list[dict[str, Any]] = []
        for chg_name, chg_artifacts in changes.items():
            flow = chg_artifacts[0].flow
            lifecycle = await _lifecycle(flow)

            phase_status: dict[str, str] = {}
            phases_out: list[dict[str, Any]] = []
            if lifecycle:
                for i, phase in enumerate(lifecycle):
                    kinds = set(phase.get("kinds", []))
                    phase_artifacts = [a for a in chg_artifacts if a.type.value in kinds] if kinds else []
                    if kinds and phase_artifacts and all(a.status.value == "archived" for a in phase_artifacts):
                        status = "done"
                    elif kinds and any(a.status.value != "archived" for a in phase_artifacts):
                        # active only if no earlier phase is still active
                        earlier = lifecycle[:i]
                        earlier_open = any(
                            any(
                                a.type.value in set(p.get("kinds", [])) and a.status.value != "archived"
                                for a in chg_artifacts
                            )
                            for p in earlier
                        )
                        status = "active" if not earlier_open else "pending"
                        # if an earlier phase is open, this one is pending;
                        # but if this phase has artifacts and earlier ones are done → active
                        if earlier_open:
                            earlier_had_artifacts = any(
                                any(a.type.value in set(p.get("kinds", [])) for a in chg_artifacts)
                                for p in earlier
                            )
                            status = "pending" if earlier_had_artifacts else "active"
                    else:
                        status = "pending"
                    phases_out.append(
                        {
                            "name": phase["name"],
                            "status": status,
                            "desc": self._PHASE_DESCS.get(phase["name"], "Complete this phase's output."),
                        }
                    )
                    phase_status[phase["name"]] = status

            tasks = [a for a in chg_artifacts if a.type.value == "task"]
            done = sum(1 for t in tasks if t.metadata.get("done"))
            updated = max((a.updated_at for a in chg_artifacts if a.updated_at), default=None)

            out.append(
                {
                    "change": chg_name,
                    "flow": flow,
                    "updated_at": _iso(updated),
                    "task_progress": {"done": done, "total": len(tasks)},
                    "phases": phases_out,
                }
            )

        out.sort(key=lambda c: c["updated_at"] or "", reverse=True)
        return out

    async def list_artifacts(
        self, slug: str, type_filter: str | None = None, flow_filter: str | None = None
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