import json
from uuid import UUID

import psycopg.rows

from opensddrag.db.connection import get_conn
from opensddrag.models.skill import Skill, SkillCreate, SkillStep


def _row_to_skill(row: dict) -> Skill:
    steps = [SkillStep(**s) for s in row["workflow_steps"]]
    return Skill(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        description=row["description"],
        workflow_steps=steps,
        metadata=row["metadata"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def create_skill(data: SkillCreate, embedding: list[float]) -> Skill:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO skills (project_id, name, description, workflow_steps, metadata, embedding)
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::vector)
                ON CONFLICT (project_id, name) DO UPDATE
                  SET description = EXCLUDED.description,
                      workflow_steps = EXCLUDED.workflow_steps,
                      metadata = EXCLUDED.metadata,
                      embedding = EXCLUDED.embedding,
                      updated_at = NOW()
                RETURNING id, project_id, name, description, workflow_steps, metadata, created_at, updated_at
                """,
                (
                    str(data.project_id) if data.project_id else None,
                    data.name,
                    data.description,
                    json.dumps([s.model_dump() for s in data.workflow_steps]),
                    json.dumps(data.metadata),
                    str(embedding),
                ),
            )
            row = await cur.fetchone()
            return _row_to_skill(row)


async def list_skills(project_id: UUID) -> list[Skill]:
    """Returns global skills (project_id IS NULL) + project-specific skills."""
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT id, project_id, name, description, workflow_steps, metadata, created_at, updated_at
                FROM skills
                WHERE project_id IS NULL OR project_id = %s
                ORDER BY project_id NULLS FIRST, name
                """,
                (str(project_id),),
            )
            rows = await cur.fetchall()
            return [_row_to_skill(r) for r in rows]


async def get_skill(name: str, project_id: UUID | None = None) -> Skill | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT id, project_id, name, description, workflow_steps, metadata, created_at, updated_at
                FROM skills
                WHERE name = %s AND (project_id IS NULL OR project_id = %s)
                ORDER BY project_id NULLS LAST
                LIMIT 1
                """,
                (name, str(project_id) if project_id else None),
            )
            row = await cur.fetchone()
            return _row_to_skill(row) if row else None


async def suggest(project_id: UUID, query_embedding: list[float], limit: int = 3) -> list[Skill]:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT id, project_id, name, description, workflow_steps, metadata, created_at, updated_at
                FROM skills
                WHERE (project_id IS NULL OR project_id = %s) AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (str(project_id), str(query_embedding), limit),
            )
            rows = await cur.fetchall()
            return [_row_to_skill(r) for r in rows]
