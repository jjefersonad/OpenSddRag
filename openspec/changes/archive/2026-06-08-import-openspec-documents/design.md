## Context

OpenSddRag already has all the infrastructure needed to store and search artifacts: `db/repository.py` exposes `create_artifact`, `update_artifact`, `link_artifacts`, and `search_semantic`; `embedding/service.py` provides `embed()`; and the CLI uses Typer sub-apps registered in `cli/main.py`. The project is missing only the discovery/parsing layer that reads OpenSpec's on-disk layout and drives these existing APIs.

OpenSpec stores planning artifacts in a well-defined directory structure:
- `openspec/changes/<change-name>/proposal.md` — why
- `openspec/changes/<change-name>/design.md` — how
- `openspec/changes/<change-name>/tasks.md` — what to do
- `openspec/changes/<change-name>/specs/<capability>/spec.md` — behavior specs
- `openspec/specs/<capability>/spec.md` — global/canonical capability specs

The `ArtifactType` enum in `models/artifact.py` has four values: `proposal`, `spec`, `task`, `design`. Note that OpenSpec's `tasks.md` maps to `ArtifactType.task` (singular).

## Goals / Non-Goals

**Goals:**
- Walk an OpenSpec project directory and ingest all recognized artifact files
- Map each file to the correct `ArtifactType`
- Compute embeddings for all imported content
- Create `depends_on` relationships matching OpenSpec's dependency order
- Be idempotent by default; accept `--force` to re-import
- Expose the feature as both a CLI command and an MCP tool

**Non-Goals:**
- Parsing or validating the internal Markdown structure of OpenSpec files (content is stored as raw Markdown)
- Syncing changes back from OpenSddRag to OpenSpec files
- Auto-detecting which OpenSpec project a Claude session is working in (user must provide the path)
- Supporting OpenSpec workspace-planning schema (multi-project changes) in this iteration

## Decisions

### 1. New CLI module: `cli/import_openspec.py`

Register a new Typer app with a single `openspec` command under a top-level `import` sub-group. Register it in `cli/main.py` as `app.add_typer(import_cmd.app, name="import")`.

**Alternative considered**: Extending an existing CLI module. Rejected because the import domain is distinct enough to deserve its own file and a clean command path (`opensddrag import openspec`).

### 2. Discovery via `pathlib.Path.glob()` — no OpenSpec CLI dependency

The importer reads the filesystem directly using `pathlib`. It does not invoke the `openspec` CLI binary.

**Rationale**: Avoids requiring `openspec` to be installed in the same environment as `opensddrag`. The on-disk format is stable and fully documented. This also makes the code easier to test.

**Pattern**:
- Changes: `<root>/openspec/changes/<change-name>/{proposal,design,tasks}.md` + `<root>/openspec/changes/<change-name>/specs/**/*.md`
- Global specs: `<root>/openspec/specs/<capability>/spec.md`

### 3. Idempotency via `metadata.source_path`

Each artifact's `metadata` will store `{"source": "openspec", "source_path": "<relative-path>", "change_name": "<name>"}`. Before inserting, the importer queries `list_artifacts` and builds a `{source_path: artifact_id}` index. Files already present are skipped (unless `--force`).

**Alternative considered**: Checking by artifact `name`. Rejected because names could collide across projects if multiple OpenSpec repos are imported.

### 4. Relationships created in a second pass

After all artifacts for a change are inserted/retrieved, a second pass creates `depends_on` links:
- each `spec` → `proposal` (same change)
- `design` → `proposal` (same change)
- `task` → all `spec` artifacts of the same change
- `task` → `design` (if present in the same change)

`link_artifacts` already silently de-duplicates on `(source_id, target_id, relationship_type)`.

### 5. MCP tool `openspec_import` wraps the same async core

The CLI and the MCP tool both call a shared async function `import_openspec_path(root, project_id, change_name, force)` in `cli/import_openspec.py`. The CLI runs it via `asyncio.run()`; the MCP tool calls it directly since the MCP server is already async.

### 6. Project slug required

Both the CLI and MCP tool accept a `--project` / `project_slug` argument. If omitted, it falls back to `settings.opensddrag_project` (same pattern used everywhere in the codebase).

## Risks / Trade-offs

- **Large files**: Embedding a very long `tasks.md` may be slow. Mitigation: the embedding model truncates at 256 tokens anyway; no special handling needed.
- **Stale `source_path` index**: If the user renames an OpenSpec change after importing, the old artifact remains and a duplicate is created on re-import without `--force`. Mitigation: document this limitation; the user can delete old artifacts manually.
- **`tasks.md` → `task` type mismatch**: OpenSpec names the file `tasks` (plural) but OpenSddRag's type is `task` (singular). The mapping is explicit in code — no ambiguity.

## Migration Plan

No database migration required. The `metadata` column (`jsonb`) already exists and supports arbitrary keys. The `source_path` key is new but additive.

Deployment: ship as a new CLI command + MCP tool. Existing artifacts are unaffected.

## Open Questions

- Should a future iteration support incremental sync (detect updated files and re-embed only changed ones)? Out of scope for now; `--force` is sufficient.
- Should the importer support OpenSpec workspace-planning schema (cross-project changes with `openspec/explorations/`)? Deferred to a follow-up.
