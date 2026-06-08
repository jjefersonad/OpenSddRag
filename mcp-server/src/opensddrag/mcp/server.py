"""OpenSddRag MCP Server — exposes Harness infrastructure via Model Context Protocol."""

import asyncio
import json
from typing import Any
from uuid import UUID

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

from opensddrag.config import settings
from opensddrag.db import (
    project_repository,
    repository,
    session_repository,
    skill_repository,
    trace_repository,
)
from opensddrag.cli._seeds import seed_sdd_skills
from opensddrag.cli.import_openspec import import_openspec_path
from opensddrag.db.connection import close_pool, run_migrations
from opensddrag.embedding.service import embed
from opensddrag.models.artifact import ArtifactCreate, ArtifactStatus, ArtifactType, ArtifactUpdate
from opensddrag.models.project import ProjectCreate
from opensddrag.models.skill import SkillCreate, SkillStep
from opensddrag.models.session import SessionUpdate
from opensddrag.models.trace import TraceCreate

server = Server("opensddrag")


# ─── Helpers ───────────────────────────────────────────────────────────────────

async def _resolve_project_id(project_slug: str | None) -> UUID:
    slug = project_slug or settings.opensddrag_project
    project = await project_repository.require_project(slug)
    return project.id


def _text(content: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=content)]


def _json(data: Any) -> list[types.TextContent]:
    return _text(json.dumps(data, default=str, indent=2, ensure_ascii=False))


# ─── Tool definitions ──────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # ── Memory: Semantic ──────────────────────────────────────────────────
        types.Tool(
            name="search_semantic",
            description="Semantic search over SDD artifacts (specs, tasks, designs) using pgvector. Pass project_slug='*' to search across all projects.",
            inputSchema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "Natural language query"},
                    "project_slug": {"type": "string", "description": "Project slug or '*' for all projects"},
                    "type": {"type": "string", "enum": ["proposal", "spec", "task", "design"]},
                    "limit": {"type": "integer", "default": 5},
                },
            },
        ),
        types.Tool(
            name="read_artifact",
            description="Read the full content of a specific SDD artifact by name.",
            inputSchema={
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "project_slug": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="list_artifacts",
            description="List SDD artifacts with optional filters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_slug": {"type": "string"},
                    "type": {"type": "string", "enum": ["proposal", "spec", "task", "design"]},
                    "status": {"type": "string", "enum": ["draft", "active", "archived"]},
                },
            },
        ),
        # ── Memory: Episodic ──────────────────────────────────────────────────
        types.Tool(
            name="recall_episodes",
            description="Semantic search over past agent execution traces (episodic memory). Useful to recall what was done before.",
            inputSchema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "project_slug": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
            },
        ),
        types.Tool(
            name="record_trace",
            description="Record an agent action to episodic memory.",
            inputSchema={
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {"type": "string", "description": "Action name, e.g. 'create_spec', 'search', 'apply_task'"},
                    "project_slug": {"type": "string"},
                    "artifact_id": {"type": "string"},
                    "query": {"type": "string"},
                    "result_summary": {"type": "string"},
                    "session_id": {"type": "string"},
                },
            },
        ),
        # ── Memory: Working Context ───────────────────────────────────────────
        types.Tool(
            name="get_working_context",
            description="Get the current working session: active artifacts, context state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_slug": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="update_working_context",
            description="Update the working session: set active artifacts or context data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_slug": {"type": "string"},
                    "session_id": {"type": "string"},
                    "active_artifact_ids": {"type": "array", "items": {"type": "string"}},
                    "context": {"type": "object"},
                },
            },
        ),
        # ── Skills ────────────────────────────────────────────────────────────
        types.Tool(
            name="list_skills",
            description="List available SDD skills (global + project-specific).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_slug": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_skill",
            description="Get the workflow steps of a specific skill by name.",
            inputSchema={
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "project_slug": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="suggest_skill",
            description="Given an objective, suggest the most relevant SDD skill using semantic search.",
            inputSchema={
                "type": "object",
                "required": ["objective"],
                "properties": {
                    "objective": {"type": "string"},
                    "project_slug": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="create_skill",
            description="Create a new skill template (project-specific or global).",
            inputSchema={
                "type": "object",
                "required": ["name", "description", "workflow_steps"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "workflow_steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["step", "instruction"],
                            "properties": {
                                "step": {"type": "integer"},
                                "instruction": {"type": "string"},
                                "artifact_type": {"type": "string"},
                                "required": {"type": "boolean"},
                            },
                        },
                    },
                    "project_slug": {"type": "string"},
                },
            },
        ),
        # ── SDD Artifacts (Protocols) ─────────────────────────────────────────
        types.Tool(
            name="create_artifact",
            description="Create a new SDD artifact (proposal, spec, change, task, design) with automatic embedding.",
            inputSchema={
                "type": "object",
                "required": ["name", "type", "content"],
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["proposal", "spec", "task", "design"]},
                    "content": {"type": "string"},
                    "project_slug": {"type": "string"},
                    "status": {"type": "string", "enum": ["draft", "active", "archived"], "default": "draft"},
                    "metadata": {"type": "object"},
                },
            },
        ),
        types.Tool(
            name="update_artifact",
            description="Update an existing SDD artifact content or status. Re-generates embedding automatically.",
            inputSchema={
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "project_slug": {"type": "string"},
                    "content": {"type": "string"},
                    "status": {"type": "string", "enum": ["draft", "active", "archived"]},
                    "metadata": {"type": "object"},
                },
            },
        ),
        types.Tool(
            name="validate_artifact",
            description="Validate the structure of an SDD artifact.",
            inputSchema={
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "project_slug": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="link_artifacts",
            description="Create a relationship between two SDD artifacts.",
            inputSchema={
                "type": "object",
                "required": ["source_name", "target_name", "relationship_type"],
                "properties": {
                    "source_name": {"type": "string"},
                    "target_name": {"type": "string"},
                    "relationship_type": {"type": "string", "enum": ["depends_on", "implements", "relates_to"]},
                    "project_slug": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_relationships",
            description="Get artifacts related to a given artifact.",
            inputSchema={
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "project_slug": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="list_projects",
            description="List all projects in the central OpenSddRag database.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="create_project",
            description="Create a new project in the OpenSddRag database. Returns the project with an already_existed flag.",
            inputSchema={
                "type": "object",
                "required": ["slug", "name"],
                "properties": {
                    "slug": {"type": "string", "description": "Unique project identifier (kebab-case)"},
                    "name": {"type": "string", "description": "Human-readable project name"},
                    "description": {"type": "string", "description": "Optional project description"},
                },
            },
        ),
        # ── OpenSpec Import ───────────────────────────────────────────────────
        types.Tool(
            name="openspec_import",
            description=(
                "Import OpenSpec planning documents (proposal.md, design.md, tasks.md, specs/**/*.md) "
                "from an OpenSpec project directory into OpenSddRag as searchable, embedded artifacts. "
                "Idempotent by default — pass force=true to re-embed existing artifacts."
            ),
            inputSchema={
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the OpenSpec project root (the directory containing openspec/)"},
                    "change": {"type": "string", "description": "Import only this change name; omit to import all changes"},
                    "project_slug": {"type": "string", "description": "Target OpenSddRag project slug; defaults to OPENSDDRAG_PROJECT env var"},
                    "force": {"type": "boolean", "description": "Re-import and re-embed artifacts that were already imported", "default": False},
                },
            },
        ),
    ]


# ─── Tool execution ────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        return await _dispatch(name, arguments)
    except ValueError as e:
        return _text(f"Error: {e}")
    except Exception as e:
        return _text(f"Unexpected error in '{name}': {type(e).__name__}: {e}")


async def _dispatch(name: str, args: dict) -> list[types.TextContent]:
    match name:
        # Memory: Semantic
        case "search_semantic":
            slug = args.get("project_slug", "*")
            embedding = embed(args["query"])
            artifact_type = ArtifactType(args["type"]) if args.get("type") else None
            if slug == "*":
                results = await repository.search_semantic("*", embedding, args.get("limit", 5), artifact_type)
            else:
                project_id = await _resolve_project_id(slug)
                results = await repository.search_semantic(project_id, embedding, args.get("limit", 5), artifact_type)
            return _json([
                {"name": a.name, "type": a.type, "status": a.status, "project_id": str(a.project_id), "content": a.content[:500]}
                for a in results
            ])

        case "read_artifact":
            project_id = await _resolve_project_id(args.get("project_slug"))
            artifact = await repository.get_artifact(project_id, args["name"])
            if not artifact:
                return _text(f"Artifact '{args['name']}' not found.")
            return _json(artifact.model_dump())

        case "list_artifacts":
            project_id = await _resolve_project_id(args.get("project_slug"))
            artifact_type = ArtifactType(args["type"]) if args.get("type") else None
            artifact_status = ArtifactStatus(args["status"]) if args.get("status") else None
            results = await repository.list_artifacts(project_id, artifact_type, artifact_status)
            return _json([{"name": a.name, "type": a.type, "status": a.status} for a in results])

        # Memory: Episodic
        case "recall_episodes":
            project_id = await _resolve_project_id(args.get("project_slug"))
            embedding = embed(args["query"])
            traces = await trace_repository.recall(project_id, embedding, args.get("limit", 5))
            return _json([
                {"action": t.action, "query": t.query, "result_summary": t.result_summary, "created_at": str(t.created_at)}
                for t in traces
            ])

        case "record_trace":
            project_id = await _resolve_project_id(args.get("project_slug"))
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
            return _text(f"Trace recorded: {trace.id}")

        # Memory: Working Context
        case "get_working_context":
            project_id = await _resolve_project_id(args.get("project_slug"))
            session = await session_repository.get_or_create(project_id)
            return _json(session.model_dump())

        case "update_working_context":
            project_id = await _resolve_project_id(args.get("project_slug"))
            session = await session_repository.get_or_create(project_id)
            update = SessionUpdate(
                active_artifact_ids=[UUID(i) for i in args["active_artifact_ids"]] if args.get("active_artifact_ids") else None,
                context=args.get("context"),
            )
            updated = await session_repository.update(project_id, session.id, update)
            return _json(updated.model_dump())

        # Skills
        case "list_skills":
            project_id = await _resolve_project_id(args.get("project_slug"))
            skills = await skill_repository.list_skills(project_id)
            return _json([{"name": s.name, "description": s.description, "global": s.project_id is None} for s in skills])

        case "get_skill":
            project_id = await _resolve_project_id(args.get("project_slug"))
            skill = await skill_repository.get_skill(args["name"], project_id)
            if not skill:
                return _text(f"Skill '{args['name']}' not found.")
            return _json(skill.model_dump())

        case "suggest_skill":
            project_id = await _resolve_project_id(args.get("project_slug"))
            embedding = embed(args["objective"])
            skills = await skill_repository.suggest(project_id, embedding)
            return _json([{"name": s.name, "description": s.description} for s in skills])

        case "create_skill":
            project_id = await _resolve_project_id(args.get("project_slug")) if args.get("project_slug") else None
            steps = [SkillStep(**s) for s in args["workflow_steps"]]
            data = SkillCreate(
                project_id=project_id,
                name=args["name"],
                description=args["description"],
                workflow_steps=steps,
            )
            embedding = embed(f"{args['name']} {args['description']}")
            skill = await skill_repository.create_skill(data, embedding)
            return _text(f"Skill '{skill.name}' created.")

        # SDD Artifacts (Protocols)
        case "create_artifact":
            project_id = await _resolve_project_id(args.get("project_slug"))
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
            return _text(f"Artifact '{artifact.name}' ({artifact.type}) created with id {artifact.id}.")

        case "update_artifact":
            project_id = await _resolve_project_id(args.get("project_slug"))
            update = ArtifactUpdate(
                content=args.get("content"),
                status=ArtifactStatus(args["status"]) if args.get("status") else None,
                metadata=args.get("metadata"),
            )
            new_embedding = embed(args["content"]) if args.get("content") else None
            artifact = await repository.update_artifact(project_id, args["name"], update, new_embedding)
            if not artifact:
                return _text(f"Artifact '{args['name']}' not found.")
            return _text(f"Artifact '{artifact.name}' updated.")

        case "validate_artifact":
            project_id = await _resolve_project_id(args.get("project_slug"))
            artifact = await repository.get_artifact(project_id, args["name"])
            if not artifact:
                return _text(f"Artifact '{args['name']}' not found.")
            issues = _validate(artifact.type.value, artifact.content)
            if issues:
                return _json({"valid": False, "issues": issues})
            return _json({"valid": True, "issues": []})

        case "link_artifacts":
            project_id = await _resolve_project_id(args.get("project_slug"))
            source = await repository.get_artifact(project_id, args["source_name"])
            target = await repository.get_artifact(project_id, args["target_name"])
            if not source:
                return _text(f"Source artifact '{args['source_name']}' not found.")
            if not target:
                return _text(f"Target artifact '{args['target_name']}' not found.")
            await repository.link_artifacts(source.id, target.id, args["relationship_type"])
            return _text(f"Linked '{source.name}' → '{target.name}' ({args['relationship_type']}).")

        case "get_relationships":
            project_id = await _resolve_project_id(args.get("project_slug"))
            artifact = await repository.get_artifact(project_id, args["name"])
            if not artifact:
                return _text(f"Artifact '{args['name']}' not found.")
            related = await repository.get_relationships(artifact.id)
            return _json(related)

        case "list_projects":
            projects = await project_repository.list_projects()
            return _json([{"id": str(p.id), "slug": p.slug, "name": p.name, "description": p.description} for p in projects])

        case "create_project":
            slug = args["slug"].strip()
            name = args["name"].strip()
            existing = await project_repository.get_project_by_slug(slug)
            if existing:
                return _json({"id": str(existing.id), "slug": existing.slug, "name": existing.name, "already_existed": True})
            project = await project_repository.create_project(
                ProjectCreate(slug=slug, name=name, description=args.get("description"))
            )
            return _json({"id": str(project.id), "slug": project.slug, "name": project.name, "already_existed": False})

        # OpenSpec Import
        case "openspec_import":
            from pathlib import Path
            project_id = await _resolve_project_id(args.get("project_slug"))
            root = Path(args["path"])
            if not root.exists():
                return _text(f"Error: path does not exist: {root}")
            result = await import_openspec_path(
                root=root,
                project_id=project_id,
                change_name=args.get("change"),
                force=args.get("force", False),
            )
            return _json({
                "imported": result.imported,
                "skipped": result.skipped,
                "failed": result.failed,
                "details": result.details,
            })

        case _:
            return _text(f"Unknown tool: {name}")


def _validate(artifact_type: str, content: str) -> list[str]:
    issues = []
    if len(content.strip()) < 10:
        issues.append("Content is too short (minimum 10 characters).")
    if artifact_type == "spec":
        if "Purpose" not in content:
            issues.append("Spec must have a 'Purpose' section.")
        if "Requirements" not in content:
            issues.append("Spec must have a 'Requirements' section.")
    if artifact_type == "task":
        if not content.strip():
            issues.append("Task content cannot be empty.")
        if "## Goal" not in content:
            issues.append("Task must have a '## Goal' section describing what this task accomplishes.")
        if "## Acceptance Criteria" not in content:
            issues.append("Task must have an '## Acceptance Criteria' section with verifiable criteria.")
    return issues


# ─── Resources ────────────────────────────────────────────────────────────────

@server.list_resources()
async def list_resources() -> list[types.Resource]:
    projects = await project_repository.list_projects()
    resources = []
    for p in projects:
        resources.append(types.Resource(
            uri=f"project://{p.slug}",
            name=f"Project: {p.name}",
            description=p.description or "",
            mimeType="application/json",
        ))
    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri.startswith("project://"):
        slug = uri.removeprefix("project://")
        project = await project_repository.get_project_by_slug(slug)
        if not project:
            return json.dumps({"error": f"Project '{slug}' not found."})
        artifacts = await repository.list_artifacts(project.id)
        return json.dumps({
            "project": project.model_dump(),
            "artifacts": [{"name": a.name, "type": a.type, "status": a.status} for a in artifacts],
        }, default=str, indent=2)
    if uri.startswith("artifact://"):
        artifact_id = uri.removeprefix("artifact://")
        artifact = await repository.get_artifact_by_id(UUID(artifact_id))
        if not artifact:
            return json.dumps({"error": "Artifact not found."})
        return json.dumps(artifact.model_dump(), default=str, indent=2)
    return json.dumps({"error": f"Unknown resource URI: {uri}"})


# ─── Entry points ─────────────────────────────────────────────────────────────

async def _bootstrap() -> None:
    await run_migrations()
    await seed_sdd_skills()


async def _main_stdio() -> None:
    await _bootstrap()
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
    await close_pool()


async def _main_sse(host: str, port: int) -> None:
    import logging
    import uvicorn
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.routing import Mount

    from opensddrag.config import settings
    from opensddrag.mcp.auth import AuthMiddleware

    await _bootstrap()

    session_manager = StreamableHTTPSessionManager(
        app=server,
        event_store=None,
        json_response=False,
    )

    class _MCPApp:
        async def __call__(self, scope, receive, send):
            await session_manager.handle_request(scope, receive, send)

    if settings.auth_enabled:
        middleware = [Middleware(AuthMiddleware)]
    else:
        logging.warning("WARNING: Auth is disabled. Do not expose this server publicly.")
        middleware = []

    app = Starlette(
        routes=[Mount("/mcp", app=_MCPApp())],
        middleware=middleware,
    )

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    srv = uvicorn.Server(config)

    async with session_manager.run():
        await srv.serve()

    await close_pool()


def run(transport: str = "stdio", host: str = "0.0.0.0", port: int = 8000) -> None:
    if transport == "sse":
        asyncio.run(_main_sse(host, port))
    else:
        asyncio.run(_main_stdio())
