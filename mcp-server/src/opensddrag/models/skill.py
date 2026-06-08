from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SkillStep(BaseModel):
    step: int
    instruction: str
    artifact_type: str | None = None
    required: bool = True


class Skill(BaseModel):
    id: UUID
    project_id: UUID | None  # None = global skill
    name: str
    description: str
    workflow_steps: list[SkillStep]
    metadata: dict
    created_at: datetime
    updated_at: datetime


class SkillCreate(BaseModel):
    project_id: UUID | None = None
    name: str
    description: str
    workflow_steps: list[SkillStep]
    metadata: dict = {}
