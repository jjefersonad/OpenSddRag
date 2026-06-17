"""Regression test for the ``run_migrations()`` bootstrap.

Reproduces the legacy pre-tracking scenario fixed by
``fix-migration-bootstrap-skip``: a database where the ``artifacts`` table
already exists but the ``schema_migrations`` tracking table is empty (or has
been dropped). The bootstrap must:

* REQ-001 — adopt only the legacy baseline (``<= 003_project_rules.sql``) and
  mark those rows in ``schema_migrations`` without executing them.
* REQ-002 — fall through to the normal loop and actually execute any newer
  migration that is not yet tracked (e.g. ``004_hybrid_search.sql``), then
  record it.
* REQ-004 — never re-run the non-idempotent baseline migrations
  (``002_fix_relationships_and_types.sql`` performs enum
  ``RENAME``/``CREATE``/``DROP`` and would corrupt an already-applied DB).
* REQ-005 — be idempotent: a second ``run_migrations()`` after a successful
  run is a no-op (no errors, ``schema_migrations`` content unchanged).

Runs against the isolated test database wired by ``tests/conftest.py``
(``TEST_DATABASE_URL`` or the local ``54327`` default). The test snapshot
restores ``schema_migrations`` to its pre-test state on teardown so it does
not leak into other tests in the suite.
"""

import pytest
import pytest_asyncio

from opensddrag.db.connection import get_conn, run_migrations


# Baseline cutoff used by run_migrations() — anything with a filename
# lexicographically <= this string is considered "legacy" and adopted by the
# bootstrap without execution.
_LEGACY_BASELINE = "003_project_rules.sql"

# Migrations that must be present in schema_migrations after the bootstrap
# adopts the baseline (sorted to match the runner's iteration order).
_EXPECTED_BASELINE = sorted(
    [
        "001_initial.sql",
        "002_api_keys.sql",
        "002_fix_relationships_and_types.sql",
        "003_project_rules.sql",
    ]
)


async def _schema_migration_filenames() -> list[str]:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT filename FROM schema_migrations")
            rows = await cur.fetchall()
    return sorted(r[0] for r in rows)


async def _column_exists(table: str, column: str) -> bool:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                  AND column_name = %s
                """,
                (table, column),
            )
            return bool(await cur.fetchone())


async def _table_exists(table: str) -> bool:
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
                """,
                (table,),
            )
            return bool(await cur.fetchone())


@pytest_asyncio.fixture
async def legacy_db_state():
    """Snapshot the test DB and reset it to the "pre-tracking legacy" state.

    The test DB normally has both ``artifacts`` and ``schema_migrations``
    populated (the previous test runs leave it in a fully-migrated state).
    This fixture truncates ``schema_migrations`` — leaving ``artifacts``
    intact — so that the next ``run_migrations()`` call hits the bootstrap
    path. On teardown the fixture restores ``schema_migrations`` by
    dropping it and re-running migrations, which brings the test DB back
    to a fully-tracked, content_tsv-present state for the rest of the suite.
    """
    # Pre-condition guard: a meaningful bootstrap test requires a legacy DB,
    # i.e. one where the artifacts table exists. If the test DB has been
    # somehow destroyed, the test is meaningless — fail loudly.
    assert await _table_exists("artifacts"), (
        "Test DB is not in a usable state: the 'artifacts' table is missing. "
        "Bring the test DB up with `docker compose -f docker-compose.test.yml "
        "up -d` and apply the baseline migrations before running this test."
    )

    # Truncate the tracking table to simulate the moment the bootstrap was
    # introduced and a legacy DB was being adopted for the first time. We
    # deliberately do NOT drop schema_migrations — recreating it inside
    # run_migrations() would still pass the "table exists" check, but
    # truncating is closer to the real-world "tracking was just added, no
    # rows yet" situation and is reversible without DDL.
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("TRUNCATE TABLE schema_migrations")

    # Sanity: confirm we are in the bug-triggering state before exercising
    # the runner.
    assert await _schema_migration_filenames() == [], (
        "Test setup failed: schema_migrations is not empty after TRUNCATE"
    )
    assert await _table_exists("artifacts"), (
        "Test setup failed: artifacts table disappeared (impossible after "
        "TRUNCATE; this is a sanity assertion about the test DB shape)."
    )

    yield

    # Teardown: drop schema_migrations and re-run migrations. The runner's
    # bootstrap will fire (artifacts exists, tracking table is freshly
    # created and empty), adopt the baseline, and the normal loop will
    # idempotently re-apply 004_hybrid_search.sql
    # (ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS). End state:
    # schema_migrations populated, content_tsv intact, artifacts rows intact.
    async with get_conn() as conn:
        await conn.execute("DROP TABLE IF EXISTS schema_migrations")
    await run_migrations()
    assert await _schema_migration_filenames() == sorted(
        [
            "001_initial.sql",
            "002_api_keys.sql",
            "002_fix_relationships_and_types.sql",
            "003_project_rules.sql",
            "004_hybrid_search.sql",
        ]
    ), "Teardown failed: schema_migrations was not fully restored."


@pytest.mark.asyncio
async def test_bootstrap_adopts_only_legacy_baseline(legacy_db_state) -> None:
    """REQ-001/REQ-002: bootstrap adopts baseline, executes newer migrations.

    With ``artifacts`` present and ``schema_migrations`` empty, the first
    ``run_migrations()`` must:
      1. Register every baseline migration (``<= _LEGACY_BASELINE``) in
         ``schema_migrations`` without executing them.
      2. Execute and register any post-baseline migration
         (``004_hybrid_search.sql``) — verified both by the row in
         ``schema_migrations`` and by the schema effect
         (``content_tsv`` column on ``artifacts``).
    """
    # 1) Baseline adopted, NOT executed. We assert "adopted" by checking
    #    the row is present in schema_migrations. We assert "not executed"
    #    implicitly: if the bootstrap were to *re-run* the non-idempotent
    #    002_fix_relationships_and_types.sql on a DB that already has the
    #    enum renamed, the `DROP TYPE` / `RENAME` chain would raise. The
    #    fact that the call below returns without exception proves REQ-004
    #    in the same breath (no enum-rename / drop-type error).
    # 2) Newer migration executed AND recorded.
    await run_migrations()

    filenames = await _schema_migration_filenames()

    # Baseline adopted (REQ-001).
    for baseline_mf in _EXPECTED_BASELINE:
        assert baseline_mf in filenames, (
            f"Bootstrap did not adopt baseline migration {baseline_mf!r}. "
            f"schema_migrations now contains: {filenames!r}"
        )

    # Post-baseline migration actually executed (REQ-002). Verified by both:
    #   (a) the row is in schema_migrations, AND
    #   (b) the schema effect (content_tsv column) is present.
    # Pre-fix behaviour: (a) was true but (b) was false — the bug.
    assert "004_hybrid_search.sql" in filenames, (
        f"Post-baseline migration 004_hybrid_search.sql was not recorded in "
        f"schema_migrations. Got: {filenames!r}"
    )
    assert await _column_exists("artifacts", "content_tsv"), (
        "Post-baseline migration 004_hybrid_search.sql was recorded in "
        "schema_migrations but its schema effect (artifacts.content_tsv) "
        "is missing — this is the exact regression: marked as applied "
        "without being executed."
    )

    # Full set check: the tracking table should now contain exactly the
    # baseline + the post-baseline file (no extras, no missing).
    expected_all = sorted(_EXPECTED_BASELINE + ["004_hybrid_search.sql"])
    assert filenames == expected_all, (
        f"schema_migrations contents do not match the expected set after "
        f"bootstrap. Expected: {expected_all!r}, got: {filenames!r}"
    )


@pytest.mark.asyncio
async def test_bootstrap_rerun_is_idempotent(legacy_db_state) -> None:
    """REQ-005: a second ``run_migrations()`` after a successful run is a no-op.

    This guards against a different regression class: the bootstrap should
    only fire when ``schema_migrations`` is empty. Once the first run has
    populated the tracking table, subsequent runs must:
      * not re-execute any migration, and
      * leave ``schema_migrations`` byte-identical (same filenames, same
        row count).
    """
    # First run: brings the legacy DB to a fully-tracked state.
    await run_migrations()
    after_first = await _schema_migration_filenames()
    first_count = len(after_first)

    # Second run: must not raise and must not change the tracking table.
    await run_migrations()
    after_second = await _schema_migration_filenames()

    assert after_first == after_second, (
        f"Second run_migrations() changed schema_migrations contents. "
        f"First:  {after_first!r}\n"
        f"Second: {after_second!r}"
    )
    assert len(after_second) == first_count, (
        f"Second run_migrations() changed the row count of "
        f"schema_migrations (was {first_count}, now {len(after_second)})."
    )

    # Belt-and-braces: assert the constant's expected value, so a future
    # rename of the baseline file produces a loud failure here rather than
    # a silent shift in bootstrap behaviour.
    from opensddrag.db.connection import _LEGACY_BASELINE  # noqa: WPS433

    assert _LEGACY_BASELINE == "003_project_rules.sql", (
        f"Baseline cutoff drifted: expected '003_project_rules.sql', "
        f"got {_LEGACY_BASELINE!r}. Update this test and the bootstrap "
        f"contract together."
    )
