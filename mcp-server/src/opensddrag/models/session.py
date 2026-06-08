from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Session(BaseModel):
    id: UUID
    project_id: UUID
    active_artifact_ids: list[UUID]
    context: dict
    started_at: datetime
    updated_at: datetime


class SessionUpdate(BaseModel):
    active_artifact_ids: list[UUID] | None = None
    context: dict | None = None
