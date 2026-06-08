from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ExecutionTrace(BaseModel):
    id: UUID
    project_id: UUID
    session_id: UUID | None
    action: str
    artifact_id: UUID | None
    query: str | None
    result_summary: str | None
    metadata: dict
    created_at: datetime


class TraceCreate(BaseModel):
    project_id: UUID
    session_id: UUID | None = None
    action: str
    artifact_id: UUID | None = None
    query: str | None = None
    result_summary: str | None = None
    metadata: dict = {}
