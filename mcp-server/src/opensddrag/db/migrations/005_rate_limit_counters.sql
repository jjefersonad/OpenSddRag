-- 005_rate_limit_counters.sql — Sliding-window counters for the `RateLimiterPort`.
--
-- Context: capability `mcp-infrastructure` of the `apply-clean-architecture-to-mcp-server` change.
-- Creates the `rate_limit_counters` table consumed by `PgRateLimiter` (see
-- `mcp-server/src/opensddrag/infrastructure/pg/pg_rate_limiter.py`, task-infra-pg-2).
-- One row per (caller_id, call timestamp); the limiter prunes rows older than
-- the configured window and counts the remainder inside a single transaction.
--
-- Spec reference: `apply-clean-architecture-to-mcp-server-mcp-infrastructure-spec`
--   REQ-002: "A `RateLimiterPort` implementation MUST persist per-caller
--            counters in PostgreSQL (new table `rate_limit_counters`) using
--            a sliding window of 60 seconds and a configurable per-profile
--            quota."
--
-- Design reference: `apply-clean-architecture-to-mcp-server-design.md`
--   Decision: "New `rate_limit_counters` table added in a new migration"
--   Risks: "Migration `005_rate_limit_counters.sql` adds DB load" — mitigated
--   by the `(caller_id, called_at DESC)` index below and the in-memory
--   fallback in `InMemoryRateLimiter` for DB outages.
--
-- This migration is behaviorally inert: the table is created but no code
-- reads from it until Phase 3 of the change (task-infra-pg-2 wires
-- `PgRateLimiter`). Until then, the table simply sits empty.

-- 1. Create the table.
--
-- `id BIGSERIAL` is not strictly required (a composite primary key on
-- (caller_id, called_at) would suffice) but BIGSERIAL is cheaper to index
-- for the `DELETE ... WHERE called_at < now() - interval '<N> seconds'`
-- prune query and keeps the row count observable via a primary key
-- constraint.
--
-- `caller_id TEXT NOT NULL` matches the domain-level `Caller.caller_id` type
-- (defined in `core/ports/authentication.py`). We do not FK to `api_keys`
-- because stdio callers use `caller_id = "stdio"` and any future JWT
-- implementation may not have a row in `api_keys`.
--
-- `called_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` — TIMESTAMPTZ (not TIMESTAMP)
-- matches the convention in `db/connection.py` and the `created_at` columns
-- of every other table.
CREATE TABLE IF NOT EXISTS rate_limit_counters (
    id BIGSERIAL PRIMARY KEY,
    caller_id TEXT NOT NULL,
    called_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Index for the sliding-window query.
--
-- The hot path is:
--   DELETE FROM rate_limit_counters
--     WHERE called_at < NOW() - INTERVAL '60 seconds'
--       AND caller_id = $1;
--   SELECT COUNT(*) FROM rate_limit_counters WHERE caller_id = $1;
-- Both predicates hit `(caller_id, called_at)` — the leading equality on
-- `caller_id` plus a range on `called_at`. A composite B-tree in
-- `(caller_id, called_at DESC)` (DESC so the most recent calls come first
-- in the index scan, which is the common case for both queries) is the
-- minimal covering index.
--
-- We do not add a separate index on `called_at` alone because no query
-- prunes or counts across all callers (the limiter is per-caller).
CREATE INDEX IF NOT EXISTS idx_rate_limit_counters_caller_time
    ON rate_limit_counters (caller_id, called_at DESC);

-- Idempotency: `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`
-- make this migration safe to re-run. The `run_migrations()` bootstrap in
-- `db/connection.py` records the filename in `schema_migrations` after a
-- successful run, so a second invocation will short-circuit at the SELECT
-- in `run_migrations()` (lines 81-88) and never re-execute this SQL.
