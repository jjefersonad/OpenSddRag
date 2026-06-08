## Why

OpenSddRag provides persistent semantic memory for AI agents, but currently has no way to ingest existing planning artifacts created by OpenSpec. Teams using OpenSpec accumulate valuable context in `proposal.md`, `design.md`, `tasks.md`, and `specs/**/*.md` files that agents cannot search or reference — this gap forces manual re-entry and breaks continuity between OpenSpec's planning phase and OpenSddRag's execution memory.

## What Changes

- Add a CLI command `opensddrag import openspec <path>` that scans an OpenSpec project directory and imports all artifacts into the OpenSddRag database
- Add an MCP tool `openspec_import` that triggers the same import from within an agent session
- Map OpenSpec artifact types (`proposal`, `spec`, `design`, `tasks`) to the corresponding OpenSddRag artifact types
- Preserve artifact relationships (e.g., specs depend on proposal, tasks depend on design + specs)
- Support importing a single change (`--change <name>`) or all changes at once
- Also import global specs from `openspec/specs/` as standalone capability artifacts
- Skip already-imported artifacts unless `--force` is passed (idempotent re-run)

## Capabilities

### New Capabilities

- `openspec-import`: CLI command and MCP tool that discovers, parses, and ingests OpenSpec documents into OpenSddRag as properly-typed, embedded artifacts with preserved relationships

### Modified Capabilities

<!-- No existing spec requirements are changing -->

## Impact

- New CLI sub-command under `opensddrag` (`opensddrag import openspec`)
- New MCP tool registered in `mcp/server.py`
- New repository method in `db/repository.py` for bulk upsert with relationship creation
- Reads from the filesystem (OpenSpec project path); no changes to OpenSpec itself
- Depends on `sentence-transformers` (already a dependency) for embedding imported content
- New optional dependency: none — OpenSpec files are plain Markdown, no special parser needed
