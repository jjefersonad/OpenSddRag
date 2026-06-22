"""Postgres-backed `ToolRegistryPort` for the 22 MCP tools.

`PgToolRegistry` is the new architecture's source of truth for *which*
tools exist and *how* they look. The tool metadata (name, description,
input schema, required permission) is **static** — it mirrors the
declarations in `mcp/server.py:list_tools()`. The matching *executor*
for each tool (the callable that does the work, extracted from the
`_dispatch` body in `mcp/server.py`) is injected at startup by
`infrastructure/composition.py` as a `dict[name -> ToolExecutorPort]`.

The "Pg" prefix is for symmetry with the other infrastructure adapters
and anticipates a future variant that hydrates tool rows from the
database; today the metadata is held in-process (see `_TOOL_DEFINITIONS`
below). The `conn_factory` is stored so the executors that need a DB
connection can be wired through the same composition root.

Per `task-infra-pg-3`, this module MUST NOT import from
`opensddrag.core.usecases` or `opensddrag.core.domain` directly. The
domain value types it needs (`Tool`, `Permission`) are re-exported by
the **ports** seam (`core.ports.tool_registry` re-exposes `Tool`,
`core.ports.authentication` re-exposes `Permission`), so the adapter
depends only on `core.ports.*` — keeping the per-file architecture grep
green.

This module is part of the **infrastructure layer**
(`infrastructure/pg/`).
"""

from __future__ import annotations

from typing import Any, Callable

# Domain value types are imported through the ports seam (NOT from
# `core.domain` directly) so the per-file architecture grep in
# `task-infra-pg-3` stays green. `Tool` lives in the namespace of
# `core.ports.tool_registry`; `Permission` lives in the namespace of
# `core.ports.authentication`.
from opensddrag.core.ports.authentication import Permission
from opensddrag.core.ports.executor import ToolExecutorPort
from opensddrag.core.ports.tool_registry import Tool, ToolRegistryPort


# ── Permission classification ────────────────────────────────────────────────
#
# Every tool defaults to `READ_ONLY`. The mutating tools — those that
# create or modify persisted state — require `WRITE`. This is the exact
# set named in `task-infra-pg-3` acceptance criteria.
_WRITE_TOOLS: frozenset[str] = frozenset(
    {
        "create_artifact",
        "update_artifact",
        "create_skill",
        "add_rule",
        "create_project",
        "openspec_import",
        "record_trace",
        "link_artifacts",
    }
)


# ── Static tool metadata ─────────────────────────────────────────────────────
#
# Mirrors `mcp/server.py:list_tools()`. Each entry is `(name, description,
# input_schema)`. The `output_schema` is `{}` (no constraint) because the
# existing MCP tools do not declare an output schema; the
# `OutputValidatorPort` treats an empty schema as "accept anything".
# Keeping this table here makes the registry independently testable
# without booting the MCP server, and lets the MCP adapter (Phase 4)
# derive `list_tools()` from the registry rather than the reverse.
_TOOL_DEFINITIONS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    # ── Memory: Semantic ─────────────────────────────────────────────────────
    (
        "search_semantic",
        "Semantic search over SDD artifacts (specs, tasks, designs) using pgvector. Pass project_slug='*' to search across all projects.",
        {
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
    (
        "read_artifact",
        "Read the full content of a specific SDD artifact by name.",
        {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "project_slug": {"type": "string"},
            },
        },
    ),
    (
        "list_artifacts",
        "List SDD artifacts with optional filters.",
        {
            "type": "object",
            "properties": {
                "project_slug": {"type": "string"},
                "type": {"type": "string", "enum": ["proposal", "spec", "task", "design"]},
                "status": {"type": "string", "enum": ["draft", "active", "archived"]},
            },
        },
    ),
    # ── Memory: Episodic ─────────────────────────────────────────────────────
    (
        "recall_episodes",
        "Semantic search over past agent execution traces (episodic memory). Useful to recall what was done before.",
        {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "project_slug": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
        },
    ),
    (
        "record_trace",
        "Record an agent action to episodic memory.",
        {
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
    # ── Memory: Working Context ──────────────────────────────────────────────
    (
        "get_working_context",
        "Get the current working session: active artifacts, context state.",
        {
            "type": "object",
            "properties": {
                "project_slug": {"type": "string"},
            },
        },
    ),
    (
        "update_working_context",
        "Update the working session: set active artifacts or context data.",
        {
            "type": "object",
            "properties": {
                "project_slug": {"type": "string"},
                "session_id": {"type": "string"},
                "active_artifact_ids": {"type": "array", "items": {"type": "string"}},
                "context": {"type": "object"},
            },
        },
    ),
    # ── Skills ───────────────────────────────────────────────────────────────
    (
        "list_skills",
        "List available SDD skills (global + project-specific).",
        {
            "type": "object",
            "properties": {
                "project_slug": {"type": "string"},
            },
        },
    ),
    (
        "get_skill",
        "Get the workflow steps of a specific skill by name.",
        {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "project_slug": {"type": "string"},
            },
        },
    ),
    (
        "suggest_skill",
        "Given an objective, suggest the most relevant SDD skill using semantic search.",
        {
            "type": "object",
            "required": ["objective"],
            "properties": {
                "objective": {"type": "string"},
                "project_slug": {"type": "string"},
            },
        },
    ),
    (
        "create_skill",
        "Create a new skill template (project-specific or global).",
        {
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
    # ── Rules (Harness) ──────────────────────────────────────────────────────
    (
        "add_rule",
        (
            "Create or upsert a project rule (idempotent on (project_slug, name)). "
            "Setting `enabled=false` soft-deletes an existing rule with the same name."
        ),
        {
            "type": "object",
            "required": ["name", "trigger", "category", "instruction"],
            "properties": {
                "name": {"type": "string", "description": "Stable rule identifier (unique per project)."},
                "trigger": {
                    "type": "string",
                    "description": "Lifecycle moment when the rule fires (one of: always, on_apply, on_verify, on_archive, on_spec).",
                },
                "category": {
                    "type": "string",
                    "description": "Rule family — one of: architecture, naming, forbidden, doc-sync, verification.",
                },
                "instruction": {"type": "string", "description": "Human-readable guidance the agent must follow."},
                "project_slug": {"type": "string", "description": "Project slug; defaults to OPENSDDRAG_PROJECT."},
                "severity": {
                    "type": "string",
                    "default": "warning",
                    "description": "How the harness should weigh a violation (error, warning, info).",
                },
                "enabled": {"type": "boolean", "default": True, "description": "False soft-deletes an existing rule."},
                "metadata": {"type": "object", "description": "Free-form JSON attached to the rule."},
            },
        },
    ),
    (
        "list_rules",
        (
            "List project rules with optional filters. By default soft-deleted "
            "rules (enabled=false) are excluded — pass enabled_only=false to "
            "include them."
        ),
        {
            "type": "object",
            "properties": {
                "project_slug": {"type": "string", "description": "Project slug; defaults to OPENSDDRAG_PROJECT."},
                "trigger": {"type": "string", "description": "Filter by trigger value."},
                "category": {"type": "string", "description": "Filter by category value."},
                "enabled_only": {"type": "boolean", "default": True},
            },
        },
    ),
    (
        "get_harness_checklist",
        (
            "Return all enabled harness rules for a given phase trigger "
            "(on_apply, on_verify, on_archive, on_spec), ordered by severity "
            "(error first) then name. Used by /opsr:apply, /opsr:verify, "
            "/opsr:archive, and /opsr:spec to present a phase-gate checklist."
        ),
        {
            "type": "object",
            "required": ["trigger"],
            "properties": {
                "trigger": {
                    "type": "string",
                    "enum": ["on_apply", "on_verify", "on_archive", "on_spec"],
                    "description": "Phase trigger to fetch rules for.",
                },
                "project_slug": {"type": "string", "description": "Project slug; defaults to OPENSDDRAG_PROJECT."},
            },
        },
    ),
    # ── SDD Artifacts (Protocols) ────────────────────────────────────────────
    (
        "create_artifact",
        "Create a new SDD artifact (proposal, spec, change, task, design) with automatic embedding.",
        {
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
    (
        "update_artifact",
        "Update an existing SDD artifact content or status. Re-generates embedding automatically.",
        {
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
    (
        "validate_artifact",
        "Validate the structure of an SDD artifact.",
        {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "project_slug": {"type": "string"},
            },
        },
    ),
    (
        "link_artifacts",
        "Create a relationship between two SDD artifacts.",
        {
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
    (
        "get_relationships",
        "Get artifacts related to a given artifact.",
        {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "project_slug": {"type": "string"},
            },
        },
    ),
    (
        "list_projects",
        "List all projects in the central OpenSddRag database.",
        {"type": "object", "properties": {}},
    ),
    (
        "create_project",
        "Create a new project in the OpenSddRag database. Returns the project with an already_existed flag.",
        {
            "type": "object",
            "required": ["slug", "name"],
            "properties": {
                "slug": {"type": "string", "description": "Unique project identifier (kebab-case)"},
                "name": {"type": "string", "description": "Human-readable project name"},
                "description": {"type": "string", "description": "Optional project description"},
            },
        },
    ),
    # ── OpenSpec Import ──────────────────────────────────────────────────────
    (
        "openspec_import",
        (
            "Import OpenSpec planning documents (proposal.md, design.md, tasks.md, specs/**/*.md) "
            "from an OpenSpec project directory into OpenSddRag as searchable, embedded artifacts. "
            "Idempotent by default — pass force=true to re-embed existing artifacts."
        ),
        {
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
)


def _required_permission(name: str) -> Permission:
    """Return `WRITE` for mutating tools, `READ_ONLY` otherwise."""
    return Permission.WRITE if name in _WRITE_TOOLS else Permission.READ_ONLY


class PgToolRegistry:
    """Static `ToolRegistryPort` over the canonical MCP tool set.

    Constructor parameters:
        conn_factory: A callable that yields a database connection (e.g.
            `opensddrag.db.connection.get_conn`). It is **not** used to
            build the tool metadata (which is static) — it is stored so
            the composition root can hand the same factory to the
            executors that need a DB connection.
        tool_executors: A `dict[name -> ToolExecutorPort]` built by the
            composition root from the extracted `_dispatch` bodies. The
            registry stores it and exposes it via `executor_for(name)`;
            it is intentionally tolerant of a partial/empty mapping so
            the registry stays unit-testable without any executors.
    """

    def __init__(
        self,
        conn_factory: Callable[..., Any],
        *,
        tool_executors: dict[str, ToolExecutorPort],
    ) -> None:
        self._conn_factory = conn_factory
        self._tool_executors: dict[str, ToolExecutorPort] = dict(tool_executors)
        self._tools: dict[str, Tool] = {}
        for name, description, input_schema in _TOOL_DEFINITIONS:
            if name in self._tools:
                raise ValueError(f"duplicate tool definition for {name!r}")
            self._tools[name] = Tool(
                name=name,
                description=description,
                required_permission=_required_permission(name),
                input_schema=input_schema,
                output_schema={},
            )

    def get(self, name: str) -> Tool | None:
        """Return the `Tool` registered under `name`, or `None`."""
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        """Return every registered `Tool`, sorted alphabetically by name."""
        return sorted(self._tools.values(), key=lambda tool: tool.name)

    def executor_for(self, name: str) -> ToolExecutorPort | None:
        """Return the executor wired for `name`, or `None` if unwired.

        Not part of `ToolRegistryPort`; used by the composition root and
        the MCP adapter to look up the callable that performs the work.
        """
        return self._tool_executors.get(name)


__all__ = ["PgToolRegistry"]
