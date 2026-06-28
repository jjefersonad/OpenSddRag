"""Per-tool executor functions — the extracted `_dispatch` bodies.

Each public function here is the work of exactly one MCP tool, lifted
out of the legacy `mcp/server.py:_dispatch()` `match` arms. They are the
concrete payload behind the `ToolExecutorPort`: the use case validates,
authorizes, and rate-limits, then calls the matching function to do the
actual work (DB reads/writes + embedding).

`PgToolExecutor` (bottom of this module) is the `ToolExecutorPort`
adapter the composition root wires in: it maps `tool.name` to the
function below, resolves the caller's `project_id`, opens a DB
connection, and `await`s the function.

Signature (per task-adapter-1):
    async def <tool>(args: dict, *, project_id, caller_id, conn) -> Any

Deviations from the literal task text, documented for the reviewer:
  * Return type is `Any`, not `dict` — several tools naturally return a
    list (`search_semantic`, `list_artifacts`, ...) or a string status
    message. Returning the **raw** value (the same value the legacy
    code passed to `_json(...)` / `_text(...)`) keeps the bodies
    verbatim; the MCP adapter serializes it. Forcing a dict wrapper
    would change the public output shape.
  * `project_id` is resolved by the bridge and passed in; tools with
    special project semantics (`search_semantic` with `'*'`,
    `create_skill` global skills) re-derive from `args` exactly as the
    legacy code did.
  * `caller_id` is accepted for forward compatibility (future per-caller
    behavior); no current tool body reads it.
  * `conn` is accepted for forward compatibility (future raw-SQL tools);
    current bodies use the async repositories, which manage their own
    pooled connections.

This module is part of the **infrastructure layer**
(`infrastructure/pg/`). It MAY import from `db/`, `embedding/`, and
`models/`. It MUST NOT import from `mcp/` (that would invert the
dependency between the adapter and the infrastructure).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import UUID

from opensddrag.config import settings
from opensddrag.core.domain.artifact_validation import validate as _validate
from opensddrag.core.domain.rule_constants import (
    VALID_HARNESS_CHECKLIST_TRIGGERS,
    VALID_RULE_CATEGORIES,
    VALID_RULE_SEVERITIES,
    VALID_RULE_TRIGGERS,
)
from opensddrag.core.domain.tool import Tool
from opensddrag.db import (
    project_repository,
    repository,
    rule_repository,
    session_repository,
    skill_repository,
    trace_repository,
)
from opensddrag.cli.import_openspec import import_openspec_path
from opensddrag.db.connection import get_conn
from opensddrag.embedding.service import embed
from opensddrag.models.artifact import (
    ArtifactCreate,
    ArtifactStatus,
    ArtifactType,
    ArtifactUpdate,
)
from opensddrag.models.project import ProjectCreate
from opensddrag.models.rule import RuleCreate
from opensddrag.models.session import SessionUpdate
from opensddrag.models.skill import SkillCreate, SkillStep
from opensddrag.models.trace import TraceCreate


async def _resolve_project_id(project_slug: str | None) -> UUID:
    """Resolve a project slug (or the configured default) to its id."""
    slug = project_slug or settings.opensddrag_project
    project = await project_repository.require_project(slug)
    return project.id


# ─── Memory: Semantic ────────────────────────────────────────────────────────


async def search_semantic(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    slug = args.get("project_slug", "*")
    query_text = args["query"]
    embedding = embed(query_text)
    artifact_type = ArtifactType(args["type"]) if args.get("type") else None
    # `query_text` is forwarded so the repository can run the hybrid lexical+vector
    # (RRF) pipeline of the `hybrid-search` capability (improve-retrieval-accuracy).
    # The MCP tool signature is unchanged; the repository falls back to the
    # pure-vector path when `settings.hybrid_search_enabled` is false or the
    # query text is empty. REQ-004 (backward-compatible search API).
    if slug == "*":
        results = await repository.search_semantic(
            "*", embedding, args.get("limit", 5), artifact_type, query_text=query_text
        )
    else:
        results = await repository.search_semantic(
            project_id,
            embedding,
            args.get("limit", 5),
            artifact_type,
            query_text=query_text,
        )
    return [
        {
            "name": a.name,
            "type": a.type,
            "status": a.status,
            "project_id": str(a.project_id),
            "content": a.content[:500],
        }
        for a in results
    ]


async def read_artifact(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    artifact = await repository.get_artifact(project_id, args["name"])
    if not artifact:
        return {"error": f"Artifact '{args['name']}' not found."}
    return artifact.model_dump()


async def list_artifacts(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    artifact_type = ArtifactType(args["type"]) if args.get("type") else None
    artifact_status = ArtifactStatus(args["status"]) if args.get("status") else None
    results = await repository.list_artifacts(
        project_id, artifact_type, artifact_status
    )
    # `id` + `updated_at` are the content-free freshness oracle for the
    # working-context content cache (working-context-content-cache REQ-008):
    # one cheap list call tells a consumer which cached entries are still fresh.
    # `updated_at` is left as a datetime so the `_json(default=str)` path
    # stringifies it identically to `read_artifact`'s model_dump, keeping the
    # cache-vs-oracle comparison byte-exact. Still content-free (no `content`).
    return [
        {
            "id": a.id,
            "name": a.name,
            "type": a.type,
            "status": a.status,
            "updated_at": a.updated_at,
        }
        for a in results
    ]


async def read_change_bundle(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    """Aggregate every artifact of a named change into one response.

    Holistic phases (verify, archive) use this to replace N point reads
    with a single call. Membership is resolved by `metadata.change_name`
    — the source of truth every phase sets at creation — NOT by
    `artifact_relationships`, which are optional and may be incomplete
    (read-change-bundle REQ-001). Proposal/design/specs carry full
    `content`; tasks are summarized to `{name, status}` and `task_count`
    makes completeness checkable (REQ-002). No `etag`/version token is
    emitted (REQ-003). Additive — no existing tool changes (REQ-004).
    """
    change_name = args["change_name"]
    artifacts = await repository.list_artifacts(project_id)
    members = [
        a for a in artifacts if (a.metadata or {}).get("change_name") == change_name
    ]
    if not members:
        return {"error": f"No artifacts found for change '{change_name}'."}

    def _first(kind: ArtifactType) -> Any:
        for a in members:
            if a.type == kind:
                return a.model_dump()
        return None

    tasks = [
        {"name": a.name, "status": a.status}
        for a in members
        if a.type == ArtifactType.task
    ]
    return {
        "proposal": _first(ArtifactType.proposal),
        "design": _first(ArtifactType.design),
        "specs": [a.model_dump() for a in members if a.type == ArtifactType.spec],
        "tasks": tasks,
        "task_count": len(tasks),
    }


# ─── Memory: Episodic ────────────────────────────────────────────────────────


async def recall_episodes(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    embedding = embed(args["query"])
    traces = await trace_repository.recall(project_id, embedding, args.get("limit", 5))
    return [
        {
            "action": t.action,
            "query": t.query,
            "result_summary": t.result_summary,
            "created_at": str(t.created_at),
        }
        for t in traces
    ]


async def record_trace(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    text = f"{args['action']} {args.get('query', '')} {args.get('result_summary', '')}"
    embedding = embed(text)
    data = TraceCreate(
        project_id=project_id,
        session_id=UUID(args["session_id"]) if args.get("session_id") else None,
        action=args["action"],
        artifact_id=UUID(args["artifact_id"]) if args.get("artifact_id") else None,
        query=args.get("query"),
        result_summary=args.get("result_summary"),
    )
    trace = await trace_repository.record(data, embedding)
    return f"Trace recorded: {trace.id}"


# ─── Memory: Working Context ──────────────────────────────────────────────────


async def get_working_context(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    session = await session_repository.get_or_create(project_id)
    always_rules = await rule_repository.list_by_trigger(
        project_id, "always", enabled_only=True
    )
    payload = session.model_dump()
    payload["rules"] = [r.model_dump() for r in always_rules]
    return payload


async def update_working_context(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    session = await session_repository.get_or_create(project_id)
    context = args.get("context")
    if context is not None:
        if "content_cache" in context:
            cache = context["content_cache"]
            if isinstance(cache, dict):
                filtered_cache = {}
                for k, v in cache.items():
                    if isinstance(v, dict):
                        t = v.get("type")
                        if t == "task" or t == ArtifactType.task.value:
                            continue
                        filtered_cache[k] = v
                context["content_cache"] = filtered_cache

    update = SessionUpdate(
        active_artifact_ids=[UUID(i) for i in args["active_artifact_ids"]]
        if args.get("active_artifact_ids")
        else None,
        context=context,
    )
    updated = await session_repository.update(project_id, session.id, update)
    return updated.model_dump()


# ─── Skills ───────────────────────────────────────────────────────────────────


async def list_skills(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    skills = await skill_repository.list_skills(project_id)
    return [
        {"name": s.name, "description": s.description, "global": s.project_id is None}
        for s in skills
    ]


async def get_skill(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    skill = await skill_repository.get_skill(args["name"], project_id)
    if not skill:
        return {"error": f"Skill '{args['name']}' not found."}
    return skill.model_dump()


async def suggest_skill(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    embedding = embed(args["objective"])
    skills = await skill_repository.suggest(project_id, embedding)
    return [{"name": s.name, "description": s.description} for s in skills]


async def create_skill(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    # Global skill when no project_slug was provided (verbatim semantics).
    effective_project_id = project_id if args.get("project_slug") else None
    steps = [SkillStep(**s) for s in args["workflow_steps"]]
    data = SkillCreate(
        project_id=effective_project_id,
        name=args["name"],
        description=args["description"],
        workflow_steps=steps,
    )
    embedding = embed(f"{args['name']} {args['description']}")
    skill = await skill_repository.create_skill(data, embedding)
    return f"Skill '{skill.name}' created."


# ─── Rules (Harness) ──────────────────────────────────────────────────────────


async def add_rule(args: dict, *, project_id: UUID | None, caller_id: str, conn) -> Any:
    trigger = args.get("trigger")
    if trigger not in VALID_RULE_TRIGGERS:
        return f"Error: Invalid trigger '{trigger}'. Valid values: {', '.join(VALID_RULE_TRIGGERS)}"
    category = args.get("category")
    if category not in VALID_RULE_CATEGORIES:
        return (
            f"Error: Invalid category '{category}'. "
            f"Valid values: {', '.join(VALID_RULE_CATEGORIES)}"
        )
    severity = args.get("severity", "warning")
    if severity not in VALID_RULE_SEVERITIES:
        return (
            f"Error: Invalid severity '{severity}'. "
            f"Valid values: {', '.join(VALID_RULE_SEVERITIES)}"
        )
    data = RuleCreate(
        project_id=project_id,
        name=args["name"],
        trigger=trigger,
        category=category,
        severity=severity,
        instruction=args["instruction"],
        enabled=bool(args.get("enabled", True)),
        metadata=args.get("metadata") or {},
    )
    rule = await rule_repository.upsert(data)
    return rule.model_dump(mode="json")


async def list_rules(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    rules = await rule_repository.list_all(
        project_id,
        trigger=args.get("trigger"),
        category=args.get("category"),
        enabled_only=bool(args.get("enabled_only", True)),
    )
    return [r.model_dump(mode="json") for r in rules]


async def get_harness_checklist(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    trigger = args.get("trigger")
    if trigger not in VALID_HARNESS_CHECKLIST_TRIGGERS:
        return (
            f"Error: Invalid trigger '{trigger}'. "
            f"Valid values: {', '.join(VALID_HARNESS_CHECKLIST_TRIGGERS)}"
        )
    rules = await rule_repository.list_by_trigger(
        project_id, trigger, enabled_only=True
    )
    return [r.model_dump() for r in rules]


# ─── SDD Artifacts (Protocols) ────────────────────────────────────────────────


async def create_artifact(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    embedding = embed(args["content"])
    data = ArtifactCreate(
        project_id=project_id,
        name=args["name"],
        type=ArtifactType(args["type"]),
        content=args["content"],
        status=ArtifactStatus(args.get("status", "draft")),
        metadata=args.get("metadata", {}),
    )
    artifact = await repository.create_artifact(data, embedding)
    return (
        f"Artifact '{artifact.name}' ({artifact.type}) created with id {artifact.id}."
    )


async def update_artifact(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    update = ArtifactUpdate(
        content=args.get("content"),
        status=ArtifactStatus(args["status"]) if args.get("status") else None,
        metadata=args.get("metadata"),
    )
    new_embedding = embed(args["content"]) if args.get("content") else None
    artifact = await repository.update_artifact(
        project_id, args["name"], update, new_embedding
    )
    if not artifact:
        return {"error": f"Artifact '{args['name']}' not found."}
    return f"Artifact '{artifact.name}' updated."


async def validate_artifact(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    artifact = await repository.get_artifact(project_id, args["name"])
    if not artifact:
        return {"error": f"Artifact '{args['name']}' not found."}
    issues = _validate(artifact.type.value, artifact.content)
    return {"valid": not issues, "issues": issues}


async def link_artifacts(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    source = await repository.get_artifact(project_id, args["source_name"])
    target = await repository.get_artifact(project_id, args["target_name"])
    if not source:
        return {"error": f"Source artifact '{args['source_name']}' not found."}
    if not target:
        return {"error": f"Target artifact '{args['target_name']}' not found."}
    await repository.link_artifacts(source.id, target.id, args["relationship_type"])
    return f"Linked '{source.name}' → '{target.name}' ({args['relationship_type']})."


async def get_relationships(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    artifact = await repository.get_artifact(project_id, args["name"])
    if not artifact:
        return {"error": f"Artifact '{args['name']}' not found."}
    return await repository.get_relationships(artifact.id)


async def list_projects(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    projects = await project_repository.list_projects()
    return [
        {"id": str(p.id), "slug": p.slug, "name": p.name, "description": p.description}
        for p in projects
    ]


async def create_project(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    slug = args["slug"].strip()
    name = args["name"].strip()
    existing = await project_repository.get_project_by_slug(slug)
    if existing:
        return {
            "id": str(existing.id),
            "slug": existing.slug,
            "name": existing.name,
            "already_existed": True,
        }
    project = await project_repository.create_project(
        ProjectCreate(slug=slug, name=name, description=args.get("description"))
    )
    return {
        "id": str(project.id),
        "slug": project.slug,
        "name": project.name,
        "already_existed": False,
    }


# ─── OpenSpec Import ──────────────────────────────────────────────────────────


async def openspec_import(
    args: dict, *, project_id: UUID | None, caller_id: str, conn
) -> Any:
    root = Path(args["path"])
    if not root.exists():
        return {"error": f"path does not exist: {root}"}
    result = await import_openspec_path(
        root=root,
        project_id=project_id,
        change_name=args.get("change"),
        force=args.get("force", False),
    )
    return {
        "imported": result.imported,
        "skipped": result.skipped,
        "failed": result.failed,
        "details": result.details,
    }


# ── Executor registry + bridge ───────────────────────────────────────────────

# Type of a single executor function.
ExecutorFn = Callable[..., Awaitable[Any]]

# `name -> function` map. The keys are the canonical MCP tool names; the
# set is exactly the 23 tools declared in `PgToolRegistry`.
EXECUTORS: dict[str, ExecutorFn] = {
    "search_semantic": search_semantic,
    "read_artifact": read_artifact,
    "list_artifacts": list_artifacts,
    "read_change_bundle": read_change_bundle,
    "recall_episodes": recall_episodes,
    "record_trace": record_trace,
    "get_working_context": get_working_context,
    "update_working_context": update_working_context,
    "list_skills": list_skills,
    "get_skill": get_skill,
    "suggest_skill": suggest_skill,
    "create_skill": create_skill,
    "add_rule": add_rule,
    "list_rules": list_rules,
    "get_harness_checklist": get_harness_checklist,
    "create_artifact": create_artifact,
    "update_artifact": update_artifact,
    "validate_artifact": validate_artifact,
    "link_artifacts": link_artifacts,
    "get_relationships": get_relationships,
    "list_projects": list_projects,
    "create_project": create_project,
    "openspec_import": openspec_import,
}


class PgToolExecutor:
    """`ToolExecutorPort` that dispatches to the extracted functions.

    On `execute(tool, parameters)` it:
        1. Resolves the caller's `project_id` from
           `parameters["project_slug"]` (None for the `'*'` wildcard, the
           configured default when absent).
        2. Opens a pooled DB connection.
        3. Awaits the matching `EXECUTORS[tool.name]` function.

    The single instance is shared across all calls (the composition root
    builds one). `caller_id` is a placeholder until the executor port
    threads the `Caller` through — no current tool body reads it.
    """

    async def execute(self, tool: Tool, parameters: dict[str, Any]) -> Any:
        func = EXECUTORS.get(tool.name)
        if func is None:
            raise KeyError(f"no executor registered for tool {tool.name!r}")
        slug = parameters.get("project_slug")
        tool_accepts_project = "project_slug" in (
            tool.input_schema.get("properties") or {}
        )
        if slug == "*":
            project_id: UUID | None = None
        elif slug is not None:
            project_id = await _resolve_project_id(slug)
        elif tool_accepts_project:
            # Caller omitted project_slug on a tool that accepts it → use default.
            project_id = await _resolve_project_id(None)
        else:
            # Global tool (e.g. list_projects, create_project) — no project context.
            project_id = None
        async with get_conn() as conn:
            return await func(
                parameters, project_id=project_id, caller_id="stdio", conn=conn
            )


__all__ = ["EXECUTORS", "PgToolExecutor"]
