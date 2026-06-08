import json
from uuid import UUID

import psycopg.rows

from opensddrag.db.connection import get_conn
from opensddrag.models.project import Project, ProjectCreate


def _row_to_project(row: dict) -> Project:
    return Project(**row)


async def create_project(data: ProjectCreate) -> Project:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO projects (slug, name, description, metadata)
                VALUES (%s, %s, %s, %s::jsonb)
                RETURNING *
                """,
                (data.slug, data.name, data.description, json.dumps(data.metadata)),
            )
            row = await cur.fetchone()
            return _row_to_project(row)


async def get_project_by_slug(slug: str) -> Project | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute("SELECT * FROM projects WHERE slug = %s", (slug,))
            row = await cur.fetchone()
            return _row_to_project(row) if row else None


async def get_project_by_id(project_id: UUID) -> Project | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute("SELECT * FROM projects WHERE id = %s", (str(project_id),))
            row = await cur.fetchone()
            return _row_to_project(row) if row else None


async def list_projects() -> list[Project]:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute("SELECT * FROM projects ORDER BY created_at DESC")
            rows = await cur.fetchall()
            return [_row_to_project(r) for r in rows]


async def require_project(slug: str) -> Project:
    project = await get_project_by_slug(slug)
    if project is None:
        raise ValueError(f"Project '{slug}' not found. Run: opensddrag project create {slug}")
    return project
