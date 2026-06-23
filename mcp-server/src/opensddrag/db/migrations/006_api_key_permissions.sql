-- 006_api_key_permissions.sql — Per-API-key permission for the new use-case auth port.
--
-- Context: capability `mcp-protocol-adapter` of the `apply-clean-architecture-to-mcp-server` change.
-- Adds a nullable `permission` column to `api_keys` so the future
-- `MCPServerAdapter._resolve_caller()` (task-adapter-1) can derive a
-- `Caller(caller_id, permission)` for the use-case `AuthenticationPort` from
-- the existing `AuthMiddleware` (mcp/auth.py) — without re-querying the DB
-- during every tool call.
--
-- Spec reference: `apply-clean-architecture-to-mcp-server-mcp-protocol-adapter-spec`
--   REQ-001 (Caller resolution): "the adapter reads `request.state.project_slug`
--   (set by `AuthMiddleware`) and, with the API key hash, derives a
--   `Caller(caller_id=key_hash[:12], permission=READ_ONLY|WRITE|ADMIN)`."
--   The middleware still validates the header and resolves the project; the
--   new column only carries the *business-level* permission that the use
--   case needs.
--
-- Design reference: `apply-clean-architecture-to-mcp-server-design.md`
--   Decision: "Reuse the existing `AuthMiddleware`; add a separate
--   use-case `AuthenticationPort`" — and the `Caller resolution` paragraph
--   that says the permission comes from a new `permission` column on
--   `api_keys` (added here), with `ADMIN` as the fallback when the column
--   is NULL.
--
-- Behavioural status: inert. The column is added but no code reads it yet.
-- The `AuthMiddleware` (mcp/auth.py) is unchanged in this change; the new
-- code path in `MCPServerAdapter._resolve_caller()` is introduced in
-- task-adapter-1, which is gated on this migration being applied.

-- 1. Add the `permission` column.
--
-- `ADD COLUMN IF NOT EXISTS` is the idempotency pattern. PostgreSQL 9.6+
-- supports it and is what 001_initial.sql already assumes (it uses
-- `CREATE EXTENSION IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS`).
--
-- The column is **nullable** by design. Existing rows (any API key created
-- before this migration) get `permission = NULL`, which the caller-resolver
-- interprets as `ADMIN` (the safe default for trusted keys issued before
-- the granular permission system existed). The check constraint below
-- accepts NULL because `permission IS NULL OR ...` short-circuits to NULL
-- for NULL inputs and PostgreSQL's CHECK constraints allow NULL by default
-- (SQL standard).
--
-- The CHECK constraint values mirror the Python `Permission` enum in
-- `core/domain/permission.py` (defined in task-domain-1):
--   READ_ONLY < WRITE < ADMIN
-- We store the enum's `.value` (the string) rather than a smallint so the
-- column is human-readable in `psql` output and future migrations / ops
-- scripts can read it without consulting the Python source.
ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS permission TEXT;

-- 2. Enforce the permission domain with a CHECK constraint.
--
-- Idempotency: `ADD CONSTRAINT IF NOT EXISTS` is **not** supported by
-- PostgreSQL for table-level CHECK constraints (unlike `ADD COLUMN IF NOT
-- EXISTS`). The portable pattern is `DROP CONSTRAINT IF EXISTS` followed
-- by `ADD CONSTRAINT`, which is a no-op when the constraint does not exist
-- and an idempotent replacement when it does (e.g. after a schema change
-- that relaxes the allowed set).
--
-- The constraint is named `api_keys_permission_check` so it shows up by
-- name in `\d api_keys` output and in any error messages raised by
-- `INSERT`/`UPDATE` of an invalid value.
--
-- We do not FK to a `permissions` lookup table because the domain is
-- closed (three values, defined in Python as an enum) and adding a table
-- would require a separate seed migration + a join on every caller resolve.
ALTER TABLE api_keys
    DROP CONSTRAINT IF EXISTS api_keys_permission_check;
ALTER TABLE api_keys
    ADD CONSTRAINT api_keys_permission_check
    CHECK (permission IS NULL OR permission IN ('READ_ONLY', 'WRITE', 'ADMIN'));

-- Idempotency: re-running this migration against a DB that already has
-- the column and constraint is a no-op. `ADD COLUMN IF NOT EXISTS` skips
-- the ADD; `DROP CONSTRAINT IF EXISTS` removes the existing constraint
-- (a no-op the first time after the first ADD); `ADD CONSTRAINT` re-adds
-- it with the same definition. Net effect on second run: zero rows changed,
-- zero errors.
--
-- The `run_migrations()` runner in db/connection.py records this filename
-- in `schema_migrations` after a successful run, so a second invocation
-- short-circuits at the SELECT in `run_migrations()` (lines 81-88) and
-- never re-executes this SQL — making the idempotency clauses a belt-
-- and-braces measure for the manual `psql -f 006_api_key_permissions.sql`
-- use case.
