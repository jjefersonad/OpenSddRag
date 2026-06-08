CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- PROJETOS (registro central — múltiplos projetos)
-- ============================================================
CREATE TABLE IF NOT EXISTS projects (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug        VARCHAR(100) UNIQUE NOT NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MEMORY: Semantic (specs, designs, tasks, proposals por projeto)
-- ============================================================
DO $$ BEGIN
    CREATE TYPE artifact_type AS ENUM ('proposal', 'spec', 'change', 'task', 'design');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE artifact_status AS ENUM ('draft', 'active', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS artifacts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    type        artifact_type NOT NULL,
    status      artifact_status NOT NULL DEFAULT 'draft',
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    embedding   vector(384),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS artifact_relationships (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id         UUID REFERENCES artifacts(id) ON DELETE CASCADE,
    target_id         UUID REFERENCES artifacts(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MEMORY: Episodic (traces de execução — por projeto)
-- ============================================================
CREATE TABLE IF NOT EXISTS execution_traces (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id     UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    session_id     UUID,
    action         VARCHAR(100) NOT NULL,
    artifact_id    UUID REFERENCES artifacts(id) ON DELETE SET NULL,
    query          TEXT,
    result_summary TEXT,
    metadata       JSONB DEFAULT '{}',
    embedding      vector(384),
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MEMORY: Working Context (sessões ativas — por projeto)
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    active_artifact_ids UUID[] DEFAULT '{}',
    context             JSONB DEFAULT '{}',
    started_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SKILLS (globais OU por projeto; project_id NULL = global)
-- ============================================================
CREATE TABLE IF NOT EXISTS skills (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id     UUID REFERENCES projects(id) ON DELETE CASCADE,
    name           VARCHAR(255) NOT NULL,
    description    TEXT NOT NULL,
    workflow_steps JSONB NOT NULL,
    metadata       JSONB DEFAULT '{}',
    embedding      vector(384),
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (project_id, name)
);

-- ============================================================
-- ÍNDICES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_artifacts_embedding ON artifacts USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_traces_embedding    ON execution_traces USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_skills_embedding    ON skills USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_artifacts_project   ON artifacts (project_id, type, status);
CREATE INDEX IF NOT EXISTS idx_traces_project      ON execution_traces (project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project    ON sessions (project_id);
