import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

import psycopg.rows

from opensddrag.db.connection import get_conn
from opensddrag.models.api_key import ApiKey


def _hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def _row_to_api_key(row: dict) -> ApiKey:
    return ApiKey(**row)


async def create_key(
    description: str,
    project_id: UUID | None = None,
    expires_at: datetime | None = None,
) -> tuple[ApiKey, str]:
    """Create a new API key. Returns (stored ApiKey, plaintext key)."""
    raw = secrets.token_hex(32)
    key_hash = _hash_key(raw)
    key_prefix = raw[:8]

    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO api_keys (key_hash, key_prefix, description, project_id, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (key_hash, key_prefix, description, str(project_id) if project_id else None, expires_at),
            )
            row = await cur.fetchone()
            return _row_to_api_key(row), raw


async def list_keys(project_id: UUID | None = None) -> list[ApiKey]:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            if project_id is None:
                await cur.execute("SELECT * FROM api_keys ORDER BY created_at DESC")
            else:
                await cur.execute(
                    "SELECT * FROM api_keys WHERE project_id = %s OR project_id IS NULL ORDER BY created_at DESC",
                    (str(project_id),),
                )
            rows = await cur.fetchall()
            return [_row_to_api_key(r) for r in rows]


async def revoke_key(key_id: UUID) -> ApiKey | None:
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                UPDATE api_keys
                SET revoked_at = NOW()
                WHERE id = %s AND revoked_at IS NULL
                RETURNING *
                """,
                (str(key_id),),
            )
            row = await cur.fetchone()
            if row:
                return _row_to_api_key(row)
            # Already revoked — return current state
            await cur.execute("SELECT * FROM api_keys WHERE id = %s", (str(key_id),))
            row = await cur.fetchone()
            return _row_to_api_key(row) if row else None


async def lookup_by_hash(plaintext: str) -> ApiKey | None:
    key_hash = _hash_key(plaintext)
    async with get_conn() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT * FROM api_keys WHERE key_hash = %s",
                (key_hash,),
            )
            row = await cur.fetchone()
            return _row_to_api_key(row) if row else None


def is_valid(key: ApiKey) -> bool:
    """Return True if the key is not revoked and not expired."""
    if key.revoked_at is not None:
        return False
    if key.expires_at is not None and key.expires_at < datetime.now(tz=timezone.utc):
        return False
    return True
