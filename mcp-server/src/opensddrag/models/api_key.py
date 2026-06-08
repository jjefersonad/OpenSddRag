from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ApiKey(BaseModel):
    id: UUID
    key_hash: str
    key_prefix: str
    description: str
    project_id: UUID | None
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
