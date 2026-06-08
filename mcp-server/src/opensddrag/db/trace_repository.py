import json
from uuid import UUID

import psycopg.rows

from opensddrag.db.connection import get_conn
from opensddrag.models.trace import ExecutionTrace, TraceCreate


def _row_to_trace(row: dict) -> ExecutionTrace:
    return ExecutionTrace(**{k: v for k, v in row.items() if k != "embedding"})


async def record(data: TraceCreate, embedding: list[float]) -> ExecutionTrace:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO execution_traces
                    (project_id, session_id, action, artifact_id, query, result_summary, metadata, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                RETURNING id, project_id, session_id, action, artifact_id, query, result_summary, metadata, created_at
                """,
                (
                    str(data.project_id),
                    str(data.session_id) if data.session_id else None,
                    data.action,
                    str(data.artifact_id) if data.artifact_id else None,
                    data.query,
                    data.result_summary,
                    json.dumps(data.metadata),
                    str(embedding),
                ),
            )
            row = await cur.fetchone()
            return _row_to_trace(row)


async def recall(project_id: UUID, query_embedding: list[float], limit: int = 5) -> list[ExecutionTrace]:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT id, project_id, session_id, action, artifact_id, query, result_summary, metadata, created_at
                FROM execution_traces
                WHERE project_id = %s AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (str(project_id), str(query_embedding), limit),
            )
            rows = await cur.fetchall()
            return [_row_to_trace(r) for r in rows]


async def list_traces(project_id: UUID, limit: int = 20) -> list[ExecutionTrace]:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT id, project_id, session_id, action, artifact_id, query, result_summary, metadata, created_at
                FROM execution_traces
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (str(project_id), limit),
            )
            rows = await cur.fetchall()
            return [_row_to_trace(r) for r in rows]
