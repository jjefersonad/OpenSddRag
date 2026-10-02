from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic_core import core_schema


class ArtifactType(str):
    """Free-text artifact kind (database-schema delta REQ-003).

    The SDD five (`proposal`, `spec`, `task`, `design`, `test`) remain
    addressable as attributes for existing callers; any other non-empty
    string is equally valid, because other flows contribute their own kinds
    via the `artifact_kinds` registry. Behaves exactly like `str` on
    serialization and comparison; a `.value` property keeps call sites that
    read `.value` working unchanged.
    """

    def __new__(cls, value: str) -> "ArtifactType":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("artifact type must be a non-empty string")
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_plain_validator_function(
            cls,
            serialization=core_schema.to_string_ser_schema(),
        )


# Built-in SDD kinds (constants, not constraints).
ArtifactType.proposal = ArtifactType("proposal")
ArtifactType.spec = ArtifactType("spec")
ArtifactType.task = ArtifactType("task")
ArtifactType.design = ArtifactType("design")
ArtifactType.test = ArtifactType("test")

ArtifactType.value = property(lambda self: str(self))

SDD_ARTIFACT_TYPES: tuple[str, ...] = (
    "proposal",
    "spec",
    "task",
    "design",
    "test",
)


class ArtifactStatus(str):
    """Status machine: draft | active | archived.

    Kept closed (a real enum) — statuses are workflow-invariant.
    """

    def __new__(cls, value: str) -> "ArtifactStatus":
        if value not in ("draft", "active", "archived"):
            raise ValueError(
                f"artifact status must be one of draft|active|archived, got {value!r}"
            )
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_plain_validator_function(
            cls,
            serialization=core_schema.to_string_ser_schema(),
        )

    def value(self) -> str:  # noqa: D401 — kept for call-site parity
        return str(self)

    draft: "ArtifactStatus" = None  # type: ignore[assignment]
    active: "ArtifactStatus" = None  # type: ignore[assignment]
    archived: "ArtifactStatus" = None  # type: ignore[assignment]


ArtifactStatus.draft = ArtifactStatus("draft")
ArtifactStatus.active = ArtifactStatus("active")
ArtifactStatus.archived = ArtifactStatus("archived")


class Artifact(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    type: ArtifactType
    status: ArtifactStatus
    flow: str = "sdd"
    content: str
    metadata: dict
    created_at: datetime
    updated_at: datetime


class ArtifactCreate(BaseModel):
    project_id: UUID
    name: str
    type: ArtifactType
    content: str
    status: ArtifactStatus | None = None
    flow: str = "sdd"
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