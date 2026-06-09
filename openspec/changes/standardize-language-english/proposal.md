## Why

The project's source code, documentation, and configuration files mix Portuguese and English, creating friction for international contributors and inconsistent developer experience. Standardizing on English for all project-level artifacts ensures the codebase is approachable and maintainable across language boundaries.

## What Changes

- Translate `README.md` (root) from Portuguese to English — it is currently fully written in Portuguese
- Translate SQL migration comments in `mcp-server/src/opensddrag/db/migrations/001_initial.sql` from Portuguese to English
- Verify and, if needed, translate any remaining Portuguese-language content in `docs/`, `client/README.md`, `client/CLAUDE.md`, and other documentation files
- **Preserved**: All database-persisted artifacts (proposals, specs, tasks, skills, traces) generated at runtime remain in the user's language — no code change affects stored content language

## Capabilities

### New Capabilities
- `project-language-standard`: Convention that all project-level text (source code, docs, comments, configs) must be in English; runtime/user-generated content in the database is language-agnostic

### Modified Capabilities
<!-- No existing spec-level capability behaviors are changing. This is a documentation and comment translation task. -->

## Impact

- `README.md` — full rewrite in English (content preserved, language changed)
- `mcp-server/src/opensddrag/db/migrations/001_initial.sql` — section-header comments translated (no schema changes)
- `docs/authorization.md`, `client/README.md`, `client/CLAUDE.md` — review and translate any Portuguese passages
- No API changes, no behavior changes, no breaking changes
