-- MIGRATION 009: web-ui-design-alignment — projects.language (project delta REQ-004)
--
-- Adds an optional `language` attribute to projects so the dashboard cards
-- can display it (design D9). Additive only: nullable TEXT, empty-string
-- semantics handled by the model default ''.
-- Idempotent: guarded by IF NOT EXISTS; re-running must be a no-op.

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT '';
