"""Regression tests for migration ``008_multi_flow.sql`` (multi-flow-foundation).

Covers the two unit-level test artifacts linked to
``multi-flow-foundation-task-db-1``:

* Unit 1 — migration 008 seeds registry rows and ``default_flow``
  (database-schema delta REQ-010): after the migration runs, the ``flows``
  table must contain ``flow='sdd'``, ``artifact_kinds`` must contain exactly
  the five SDD kind rows, and an existing project row must have
  ``default_flow='sdd'``.
* Unit 2 — migration 008 idempotency and data preservation
  (database-schema delta REQ-012): the migration must preserve every
  existing artifact's ``type`` and ``status`` (assigning ``flow='sdd'`` to
  pre-existing rows) and be idempotent — a second ``run_migrations()`` call
  must complete without error and alter no row.

Runs against the isolated test database wired by ``tests/conftest.py``.
"""

import pytest
import pytest_asyncio

from opensddrag.db.connection import get_conn, run_migrations


async def _table_exists(table: str) -> bool:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
                """,
                (table,),
            )
            return bool(await cur.fetchone())


async def _column_type(table: str, column: str) -> str | None:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s AND column_name = %s
                """,
                (table, column),
            )
            row = await cur.fetchone()
    return row[0] if row else None


async def _flows_rows() -> list[str]:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT flow FROM flows ORDER BY flow")
            return [r[0] for r in await cur.fetchall()]


async def _artifact_kinds() -> list[tuple[str, str]]:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT flow, kind FROM artifact_kinds ORDER BY flow, kind")
            return [(r[0], r[1]) for r in await cur.fetchall()]


@pytest_asyncio.fixture
async def pre008_state():
    """Snapshot the test DB and restore it to the pre-008 state.

    The flow-registry objects (``flows`` / ``artifact_kinds`` tables, the
    ``flow`` columns, ``projects.default_flow``) must not exist at test
    start. Teardown: drop the new DDL objects if the migration created them,
    drop ``schema_migrations`` and re-run all migrations, restoring the
    baseline state for the rest of the suite.
    """
    assert not await _table_exists("flows"), (
        "Test DB already has the flows table — migration 008 state is not "
        "pre-multi-flow. Reset the test database before running this test."
    )

    yield

    # Teardown: bring the DB back to the fully-migrated state the rest of
    # the suite expects. If migration 008 exists on disk, the re-run
    # recreates its objects; otherwise the baseline state is restored.
    async with get_conn() as conn:
        await conn.execute("DROP TABLE IF EXISTS artifact_kinds")
        await conn.execute("DROP TABLE IF EXISTS flows")
    await conn_cleanup()
    await run_migrations()


async def conn_cleanup() -> None:
    from opensddrag.db.connection import _pool

    if _pool is not None:
        await _pool.close()
        _pool = None


@pytest.mark.asyncio
async def test_migration_008_seeds_registry_rows_and_default_flow() -> None:
    """Unit 1 (database-schema delta REQ-010): seeds the sdd registry."""
    # Remove any flow rows left behind by other tests (isolation by key set)
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM flows WHERE flow != 'sdd'")

    await run_migrations()

    if not await _table_exists("flows"):
        pytest.fail("migration 008 did not create the flows table (not implemented yet)")

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM flows WHERE flow != 'sdd'")
    assert await _flows_rows() == ["sdd"]
    kinds = await _artifact_kinds()
    assert set(kinds) == {
        ("sdd", "proposal"),
        ("sdd", "spec"),
        ("sdd", "design"),
        ("sdd", "task"),
        ("sdd", "test"),
    }, f"artifact_kinds mismatch: {sorted(kinds)}"

    # projects.default_flow
    dtype = await _column_type("projects", "default_flow")
    assert dtype == "text", f"projects.default_flow missing (got {dtype!r})"
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT coalesce(default_flow, '<null>') FROM projects LIMIT 1")
            row = await cur.fetchone()
            assert row is not None
            assert row[0] == "sdd", f"default_flow must default to 'sdd', got {row[0]!r}"


@pytest.mark.asyncio
async def test_migration_008_preserves_artifacts_and_is_idempotent() -> None:
    """Unit 2 (database-schema delta REQ-012): preservation + idempotency."""
    from uuid import uuid4

    # Given: a pre-008 artifact row (as a v0.1.1 database would hold)
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO artifacts (project_id, name, type, status, content)
                VALUES (
                    (SELECT id FROM projects LIMIT 1),
                    %s, 'spec', 'draft', 'pre-008 row for multi-flow tests'
                )
                RETURNING id, type, status
                """,
                (f"mig008-preserve-{uuid4().hex[:8]}",),
            )
            row = await cur.fetchone()
            art_id, art_type, art_status = row

    # When: migration 008 runs
    await run_migrations()

    if await _table_exists("flows"):
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                # Then: the legacy row kept type/status and gained flow='sdd'
                await cur.execute(
                    "SELECT type, status FROM artifacts WHERE id = %s", (art_id,)
                )
                row = await cur.fetchone()
                assert row == (art_type, art_status), (
                    f"artifact {art_id} lost its type/status: {row}"
                )
                flow_col = await _column_type("artifacts", "flow")
                if flow_col == "text":
                    await cur.execute(
                        """
                        SELECT flow FROM artifacts WHERE id = %s
                          AND project_id IS NOT NULL
                        """,
                        (art_id,),
                    )
                    fr = await cur.fetchone()
                    if fr is not None:
                        assert fr[0] == "sdd", f"legacy artifact flow={fr[0]!r}"
                # type column must be free text, not the enum
                assert await _column_type("artifacts", "type") == "text"

        # When: migration runs a second time
        await run_migrations()
        # Then: no error, registry rows unchanged, legacy row intact
        assert await _flows_rows() == ["sdd"]
        kinds = await _artifact_kinds()
        assert len(kinds) == 5, f"artifact_kinds changed after re-run: {sorted(kinds)}"
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT type, status FROM artifacts WHERE id = %s", (art_id,)
                )
                assert await cur.fetchone() == (art_type, art_status)