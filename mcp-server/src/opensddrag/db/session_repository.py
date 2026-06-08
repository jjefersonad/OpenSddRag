import json
from uuid import UUID

import psycopg.rows

from opensddrag.db.connection import get_conn
from opensddrag.models.session import Session, SessionUpdate


def _row_to_session(row: dict) -> Session:
    return Session(**row)


async def get_or_create(project_id: UUID) -> Session:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT * FROM sessions WHERE project_id = %s ORDER BY updated_at DESC LIMIT 1",
                (str(project_id),),
            )
            row = await cur.fetchone()
            if row:
                return _row_to_session(row)
            await cur.execute(
                "INSERT INTO sessions (project_id) VALUES (%s) RETURNING *",
                (str(project_id),),
            )
            row = await cur.fetchone()
            return _row_to_session(row)


async def update(project_id: UUID, session_id: UUID, data: SessionUpdate) -> Session:
    sets = ["updated_at = NOW()"]
    params: list = []
    if data.active_artifact_ids is not None:
        sets.append("active_artifact_ids = %s::uuid[]")
        params.append([str(uid) for uid in data.active_artifact_ids])
    if data.context is not None:
        sets.append("context = %s::jsonb")
        params.append(json.dumps(data.context))
    params.extend([str(project_id), str(session_id)])
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                f"UPDATE sessions SET {', '.join(sets)} WHERE project_id = %s AND id = %s RETURNING *",
                params,
            )
            row = await cur.fetchone()
            return _row_to_session(row)
