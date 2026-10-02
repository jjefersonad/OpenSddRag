-- MIGRATION 008: multi-flow-foundation — flow registry + free-text types
-- Change: multi-flow-foundation (database-schema delta, REQ-003/007/008/010/011/012)
--
-- Decouples the core from SDD so multiple workflows ("flows") become data:
--   * artifacts.type migrates from the `artifact_type` enum to plain TEXT
--   * new `flow` column on artifacts / skills / project_rules (default 'sdd')
--   * projects.default_flow column (default 'sdd')
--   * harness trigger CHECK widened to free text (constraint dropped)
--   * new registry tables: flows, artifact_kinds (seeded with the sdd flow)
--   * filtered-list index replaced with (project_id, flow, type, status)
-- Idempotent: every step is guarded (IF EXISTS / IF NOT EXISTS / DO blocks);
-- re-running must be a no-op (REQ-012 scenario 2).

-- ─── Registry tables (REQ-010) ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS flows (
    flow           TEXT PRIMARY KEY,
    manifest       JSONB        NOT NULL,
    registered_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS artifact_kinds (
    flow    TEXT    NOT NULL REFERENCES flows(flow) ON DELETE CASCADE,
    kind    TEXT    NOT NULL,
    rules   JSONB   NOT NULL DEFAULT '{}',
    PRIMARY KEY (flow, kind)
);

-- Seed the sdd flow rows (idempotent)
INSERT INTO flows (flow, manifest)
VALUES ('sdd', '{"flow": "sdd"}'::jsonb)
ON CONFLICT (flow) DO NOTHING;

INSERT INTO artifact_kinds (flow, kind, rules)
VALUES
    ('sdd', 'proposal', '{}'::jsonb),
    ('sdd', 'spec',     '{}'::jsonb),
    ('sdd', 'design',   '{}'::jsonb),
    ('sdd', 'task',     '{}'::jsonb),
    ('sdd', 'test',     '{}'::jsonb)
ON CONFLICT (flow, kind) DO NOTHING;

-- ─── projects.default_flow (REQ-010) ─────────────────────────────────────────
ALTER TABLE projects ADD COLUMN IF NOT EXISTS default_flow TEXT NOT NULL DEFAULT 'sdd';

-- ─── artifacts: type enum → text, flow column (REQ-003) ─────────────────────
-- ─── artifacts: type enum → text, flow column (REQ-003) ─────────────────────
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'artifact_type') THEN
        -- Strip the type-dependent default so it cannot pin the enum down.
        ALTER TABLE artifacts ALTER COLUMN type DROP DEFAULT;
        ALTER TABLE artifacts
            ALTER COLUMN type TYPE TEXT
            USING type::text;
        DROP TYPE IF EXISTS artifact_type;
    END IF;
END $$;

ALTER TABLE artifacts ALTER COLUMN type SET DEFAULT 'proposal';
ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS flow TEXT NOT NULL DEFAULT 'sdd';

-- ─── skills.flow (REQ-007) ───────────────────────────────────────────────────
ALTER TABLE skills ADD COLUMN IF NOT EXISTS flow TEXT NOT NULL DEFAULT 'sdd';

-- ─── project_rules: trigger free text + flow column (REQ-011) ───────────────
ALTER TABLE project_rules ADD COLUMN IF NOT EXISTS flow TEXT NOT NULL DEFAULT 'sdd';
ALTER TABLE project_rules
    DROP CONSTRAINT IF EXISTS project_rules_trigger_check;

-- ─── Filtered-list index replacement (REQ-008) ──────────────────────────────
DROP INDEX IF EXISTS idx_artifacts_project;
CREATE INDEX IF NOT EXISTS idx_artifacts_project
    ON artifacts (project_id, flow, type, status);