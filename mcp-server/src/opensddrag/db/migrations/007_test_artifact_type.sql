-- 007_test_artifact_type.sql — Add the `test` value to `artifact_type`.
--
-- Context: capability `unified-test-artifact-type` of the
-- `embed-tdd-in-sdd-workflow` change (task-db-1).
--
-- Spec reference: `embed-tdd-in-sdd-workflow-unified-test-artifact-type-spec`
--   REQ-001 — "The `artifacts.type` enum SHALL include the value `test`."
--
-- Design reference: `embed-tdd-in-sdd-workflow-design`
--   Decision: "Casos de teste como artifact `type=\"test\"` (não tabela SQL
--   nova, não texto livre)" — scenario- and unit-level test cases become
--   first-class artifacts (`metadata.level`, `metadata.test_status`) instead
--   of a dedicated table, reusing the existing artifacts infrastructure
--   (embedding, HNSW index, relationships, semantic search).
--
-- `ALTER TYPE ... ADD VALUE` is additive and non-blocking on PostgreSQL 16 —
-- no rollback of existing data is required, and it is safe to run against a
-- live database. It is NOT transactional together with other DDL in the same
-- migration file on older PostgreSQL versions, so this migration contains
-- nothing else.
--
-- Idempotency: `ADD VALUE IF NOT EXISTS` (supported since PostgreSQL 12)
-- makes a second run a no-op instead of erroring on "already exists" — the
-- same belt-and-braces posture as `006_api_key_permissions.sql`, even though
-- `run_migrations()` already skips files it has recorded as applied.
--
-- Post-multi-flow note (008_multi_flow.sql): on a database where 008 already
-- ran, the `artifact_type` enum no longer exists (artifacts.type became
-- plain text) — but the run_migrations() bootstrap on legacy databases only
-- adopts files <= 003, so a legacy DB replaying this migration without the
-- tracking table may still hit 007 *before* 008. On fresh DBs the enum does
-- not exist and 001 already created artifacts.type as text via the
-- multi-flow baseline; guard the ADD VALUE so both worlds work.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'artifact_type') THEN
        ALTER TYPE artifact_type ADD VALUE IF NOT EXISTS 'test';
    END IF;
END $$;
