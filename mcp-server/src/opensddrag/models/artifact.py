from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class ArtifactType(str, Enum):
    proposal = "proposal"
    spec = "spec"
    task = "task"
    design = "design"


class ArtifactStatus(str, Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class Artifact(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    type: ArtifactType
    status: ArtifactStatus
    content: str
    metadata: dict
    created_at: datetime
    updated_at: datetime


class ArtifactCreate(BaseModel):
    project_id: UUID
    name: str
    type: ArtifactType
    content: str
    status: ArtifactStatus = ArtifactStatus.draft
    metadata: dict = {}


class ArtifactUpdate(BaseModel):
    content: str | None = None
    status: ArtifactStatus | None = None
    metadata: dict | None = None


class ArtifactRelationship(BaseModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    relationship_type: str
    created_at: datetime
