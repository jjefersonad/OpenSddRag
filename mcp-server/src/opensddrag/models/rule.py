from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RuleSummary(BaseModel):
    """Lightweight projection of a project rule used for list-style outputs.

    Carries only the fields needed to render or evaluate a rule, without the
    persistence metadata (id, timestamps) that callers of list endpoints do
    not need.
    """

    name: str
    category: str
    severity: str
    instruction: str


class Rule(BaseModel):
    """Full representation of a project rule as stored in `project_rules`."""

    id: UUID
    project_id: UUID
    name: str
    trigger: str
    category: str
    severity: str
    instruction: str
    enabled: bool
    metadata: dict
    created_at: datetime
    updated_at: datetime


class RuleCreate(BaseModel):
    """Input payload for inserting or upserting a project rule.

    `severity`, `enabled`, and `metadata` carry sensible defaults so that
    callers can create the most common rules (active, warning-level, with
    no extra metadata) by providing only the required fields.
    """

    project_id: UUID
    name: str
    trigger: str
    category: str
    severity: str = "warning"
    instruction: str
    enabled: bool = True
    metadata: dict = {}
