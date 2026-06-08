-- ============================================================
-- MIGRATION 002: fix artifact_relationships + artifact_type enum
-- ============================================================

-- STEP 1: Deduplicate artifact_relationships before adding UNIQUE constraint
-- Keep the oldest row (smallest id) for each (source_id, target_id, relationship_type)
DELETE FROM artifact_relationships a
USING artifact_relationships b
WHERE a.id > b.id
  AND a.source_id = b.source_id
  AND a.target_id = b.target_id
  AND a.relationship_type = b.relationship_type;

-- STEP 2: Add UNIQUE constraint so ON CONFLICT DO NOTHING actually works
ALTER TABLE artifact_relationships
    ADD CONSTRAINT uq_artifact_relationships
    UNIQUE (source_id, target_id, relationship_type);

-- STEP 3: Remove unused 'change' value from artifact_type ENUM
-- Guard: fail fast if any artifact with type='change' still exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM artifacts WHERE type = 'change') THEN
        RAISE EXCEPTION
            'Cannot remove artifact_type value ''change'': rows with type=''change'' exist. '
            'Run: DELETE FROM artifacts WHERE type = ''change''; first.';
    END IF;
END $$;

-- Rename old enum, create new enum without 'change', update column, drop old enum
ALTER TYPE artifact_type RENAME TO artifact_type_old;

DO $$ BEGIN
    CREATE TYPE artifact_type AS ENUM ('proposal', 'spec', 'task', 'design');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE artifacts
    ALTER COLUMN type TYPE artifact_type
    USING type::text::artifact_type;

DROP TYPE artifact_type_old;
