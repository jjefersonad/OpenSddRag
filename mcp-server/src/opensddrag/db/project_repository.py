import json
from uuid import UUID

import psycopg
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
                INSERT INTO projects (slug, name, description, metadata, language)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                RETURNING *
                """,
                (data.slug, data.name, data.description, json.dumps(data.metadata), data.language),
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


async def update_project(
    slug: str,
    *,
    name: str | None = None,
    description: str | None = None,
    language: str | None = None,
    new_slug: str | None = None,
) -> Project | None:
    sets = ["updated_at = NOW()"]
    params: list = []
    if name is not None:
        sets.append("name = %s")
        params.append(name)
    if description is not None:
        sets.append("description = %s")
        params.append(description)
    if language is not None:
        sets.append("language = %s")
        params.append(language)
    if new_slug is not None:
        sets.append("slug = %s")
        params.append(new_slug)
    params.append(slug)
    try:
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    f"""
                    UPDATE projects SET {", ".join(sets)}
                    WHERE slug = %s
                    RETURNING *
                    """,
                    params,
                )
                row = await cur.fetchone()
                return _row_to_project(row) if row else None
    except psycopg.errors.UniqueViolation as exc:
        raise ValueError(f"project slug {new_slug!r} already exists") from exc


async def delete_project(slug: str) -> bool:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM projects WHERE slug = %s", (slug,))
            return cur.rowcount > 0


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
