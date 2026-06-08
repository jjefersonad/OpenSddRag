from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Project(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None
    metadata: dict
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    slug: str
    name: str
    description: str | None = None
    metadata: dict = {}
