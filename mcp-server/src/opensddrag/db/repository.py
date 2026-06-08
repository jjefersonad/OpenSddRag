import json
from typing import Literal
from uuid import UUID

import psycopg.rows

from opensddrag.db.connection import get_conn
from opensddrag.models.artifact import (
    Artifact,
    ArtifactCreate,
    ArtifactRelationship,
    ArtifactStatus,
    ArtifactType,
    ArtifactUpdate,
)


def _row_to_artifact(row: dict) -> Artifact:
    return Artifact(**{k: v for k, v in row.items() if k != "embedding"})


async def create_artifact(data: ArtifactCreate, embedding: list[float]) -> Artifact:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO artifacts (project_id, name, type, status, content, metadata, embedding)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                RETURNING id, project_id, name, type, status, content, metadata, created_at, updated_at
                """,
                (
                    str(data.project_id),
                    data.name,
                    data.type.value,
                    data.status.value,
                    data.content,
                    json.dumps(data.metadata),
                    str(embedding),
                ),
            )
            row = await cur.fetchone()
            return _row_to_artifact(row)


async def get_artifact(project_id: UUID, name: str) -> Artifact | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT id, project_id, name, type, status, content, metadata, created_at, updated_at
                FROM artifacts WHERE project_id = %s AND name = %s
                """,
                (str(project_id), name),
            )
            row = await cur.fetchone()
            return _row_to_artifact(row) if row else None


async def get_artifact_by_id(artifact_id: UUID) -> Artifact | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT id, project_id, name, type, status, content, metadata, created_at, updated_at
                FROM artifacts WHERE id = %s
                """,
                (str(artifact_id),),
            )
            row = await cur.fetchone()
            return _row_to_artifact(row) if row else None


async def list_artifacts(
    project_id: UUID,
    type: ArtifactType | None = None,
    status: ArtifactStatus | None = None,
) -> list[Artifact]:
    conditions = ["project_id = %s"]
    params: list = [str(project_id)]
    if type:
        conditions.append("type = %s")
        params.append(type.value)
    if status:
        conditions.append("status = %s")
        params.append(status.value)
    where = " AND ".join(conditions)
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                f"""
                SELECT id, project_id, name, type, status, content, metadata, created_at, updated_at
                FROM artifacts WHERE {where} ORDER BY updated_at DESC
                """,
                params,
            )
            rows = await cur.fetchall()
            return [_row_to_artifact(r) for r in rows]


async def update_artifact(
    project_id: UUID,
    name: str,
    data: ArtifactUpdate,
    embedding: list[float] | None = None,
) -> Artifact | None:
    sets = ["updated_at = NOW()"]
    params: list = []
    if data.content is not None:
        sets.append("content = %s")
        params.append(data.content)
    if data.status is not None:
        sets.append("status = %s")
        params.append(data.status.value)
    if data.metadata is not None:
        sets.append("metadata = jsonb_strip_nulls(metadata || %s::jsonb)")
        params.append(json.dumps(data.metadata))
    if embedding is not None:
        sets.append("embedding = %s::vector")
        params.append(str(embedding))
    params.extend([str(project_id), name])
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                f"""
                UPDATE artifacts SET {', '.join(sets)}
                WHERE project_id = %s AND name = %s
                RETURNING id, project_id, name, type, status, content, metadata, created_at, updated_at
                """,
                params,
            )
            row = await cur.fetchone()
            return _row_to_artifact(row) if row else None


async def search_semantic(
    project_id: UUID | Literal["*"],
    query_embedding: list[float],
    limit: int = 5,
    type: ArtifactType | None = None,
) -> list[Artifact]:
    conditions = []
    filter_params: list = []
    if project_id != "*":
        conditions.append("project_id = %s")
        filter_params.append(str(project_id))
    if type:
        conditions.append("type = %s")
        filter_params.append(type.value)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    vec = str(query_embedding)
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                f"""
                SELECT id, project_id, name, type, status, content, metadata, created_at, updated_at
                FROM artifacts
                {where}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                filter_params + [vec, limit],
            )
            rows = await cur.fetchall()
            return [_row_to_artifact(r) for r in rows]


async def link_artifacts(source_id: UUID, target_id: UUID, relationship_type: str) -> ArtifactRelationship:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO artifact_relationships (source_id, target_id, relationship_type)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING *
                """,
                (str(source_id), str(target_id), relationship_type),
            )
            row = await cur.fetchone()
            # If ON CONFLICT DO NOTHING didn't return a row, fetch existing
            if row is None:
                await cur.execute(
                    """
                    SELECT * FROM artifact_relationships
                    WHERE source_id = %s AND target_id = %s AND relationship_type = %s
                    """,
                    (str(source_id), str(target_id), relationship_type),
                )
                row = await cur.fetchone()
            return ArtifactRelationship(**row)


async def get_relationships(artifact_id: UUID) -> list[dict]:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT r.relationship_type, r.created_at,
                       a.id, a.name, a.type, a.status, a.project_id
                FROM artifact_relationships r
                JOIN artifacts a ON (a.id = r.target_id OR a.id = r.source_id)
                WHERE (r.source_id = %s OR r.target_id = %s) AND a.id != %s
                """,
                (str(artifact_id), str(artifact_id), str(artifact_id)),
            )
            return await cur.fetchall()
