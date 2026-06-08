from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
from psycopg_pool import AsyncConnectionPool

from opensddrag.config import settings

_pool: AsyncConnectionPool | None = None


async def get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=10,
            open=False,
        )
        await _pool.open()
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_conn():
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute("SET search_path TO public")
        yield conn


async def run_migrations() -> None:
    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))
    async with get_conn() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        # Bootstrap: if tracking table was just created and pre-existing tables
        # are present, mark all migration files as applied to avoid re-running them.
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM schema_migrations")
            count_row = await cur.fetchone()
            if count_row and count_row[0] == 0:
                await cur.execute(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'artifacts'
                    """
                )
                if await cur.fetchone():
                    for mf in migration_files:
                        await cur.execute(
                            "INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
                            (mf.name,),
                        )
                    return

        for migration_file in migration_files:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM schema_migrations WHERE filename = %s",
                    (migration_file.name,),
                )
                if await cur.fetchone():
                    continue
            sql = migration_file.read_text()
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)",
                (migration_file.name,),
            )
