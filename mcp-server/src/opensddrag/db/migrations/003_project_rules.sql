-- 003_project_rules.sql — Harness rules: persistent per-project behavioral constraints

CREATE TABLE IF NOT EXISTS project_rules (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    trigger     TEXT        NOT NULL
                            CHECK (trigger IN ('always','on_apply','on_verify','on_archive','on_spec')),
    category    TEXT        NOT NULL
                            CHECK (category IN ('architecture','naming','forbidden','doc-sync','verification')),
    severity    TEXT        NOT NULL DEFAULT 'warning'
                            CHECK (severity IN ('error','warning','info')),
    instruction TEXT        NOT NULL,
    enabled     BOOLEAN     NOT NULL DEFAULT TRUE,
    metadata    JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, name)
);

CREATE INDEX IF NOT EXISTS idx_project_rules_lookup
    ON project_rules(project_id, trigger, enabled);
