"""Request/response DTOs for the /api/v1 management REST adapter.

Per the web-management-system web-api-management delta REQ-003 and the
mcp-server delta REQ-012, plus the delivery-adapter DTO rule of
`docs/backend-architecture.md`: REST handlers never expose repository
models (`models/`) directly — everything crossing the HTTP boundary is a
DTO defined here.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


# Kebab-case slug pattern required by project-management REQ-002:
# `^[a-z0-9]+(-[a-z0-9]+)*$`.
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Valid artifact types (mirrors the `artifacts.type` DB enum).
ArtifactType = str  # proposal | spec | design | task | test (validated at the router)


# ── Error envelope (web-api-management REQ-003) ──────────────────────────────


class ErrorEnvelope(BaseModel):
    """Shared REST error envelope — same shape as MCP tool errors.

    Serializes as `{"error": {"code": <UPPER_SNAKE>, "message": ..., "details": [...]}}`;
    `details` is omitted when not provided.
    """

    code: str
    message: str
    details: list[Any] | None = None

    def to_struct(self) -> dict[str, Any]:
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            body["details"] = self.details
        return {"error": body}


# ── Projects (project-management REQ-001/002/003) ────────────────────────────


class ProjectCreate(BaseModel):
    """REST DTO for POST /api/v1/projects.

    NOTE: deliberately distinct from `models.project.ProjectCreate` (the
    persistence-layer input used by the CLI and MCP tool executors).
    Routers translate web DTOs → repository models at the boundary.
    """

    name: str
    slug: str
    description: str = ""
    language: str = ""

    @field_validator("slug")
    @classmethod
    def slug_must_be_kebab_case(cls, value: str) -> str:
        # project-management REQ-002: `^[a-z0-9]+(-[a-z0-9]+)*$`.
        if not SLUG_PATTERN.fullmatch(value or ""):
            raise ValueError(
                "slug must be kebab-case: lowercase letters/digits "
                "separated by single hyphens"
            )
        return value


class ProjectOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


# ── Artifacts (artifact management; names/types follow the SDD lifecycle) ────


class ArtifactCreate(BaseModel):
    name: str
    type: str
    content: str
    metadata: dict[str, Any] | None = None


class ArtifactUpdate(BaseModel):
    content: str | None = None
    metadata: dict[str, Any] | None = None
    status: str | None = None


class ArtifactOut(BaseModel):
    id: str
    name: str
    type: str
    status: str
    metadata: dict[str, Any] | None = None
    content: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class RelationshipCreate(BaseModel):
    relationship_type: str  # implements | depends_on | relates_to
    target_name: str | None = None
    target_id: str | None = None


# ── Harness rules ────────────────────────────────────────────────────────────


class RuleCreate(BaseModel):
    name: str
    trigger: str  # always | on_spec | on_apply | on_verify | on_archive
    category: str  # architecture | naming | forbidden | doc-sync | verification
    severity: str = "info"  # error | warning | info
    instruction: str


class RuleToggle(BaseModel):
    enabled: bool


class RuleOut(BaseModel):
    id: str
    name: str
    trigger: str
    category: str
    severity: str
    instruction: str
    enabled: bool = True


# ── Tasks (web-api-management REQ-004) ───────────────────────────────────────


class TaskUpdate(BaseModel):
    done: bool


# ── Search (web-api-management REQ-005) ──────────────────────────────────────


class SearchOut(BaseModel):
    type: str
    title: str
    snippet: str
    project: str
    slug: str | None = None
    score: float


__all__ = [
    "SLUG_PATTERN",
    "ArtifactCreate",
    "ArtifactOut",
    "ArtifactUpdate",
    "ErrorEnvelope",
    "ProjectCreate",
    "ProjectOut",
    "RelationshipCreate",
    "RuleCreate",
    "RuleOut",
    "RuleToggle",
    "SearchOut",
    "TaskUpdate",
]