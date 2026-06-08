## 1. Core import logic

- [x] 1.1 Create `mcp-server/src/opensddrag/cli/import_openspec.py` with the async `import_openspec_path(root, project_id, change_name, force)` function
- [x] 1.2 Implement `_discover_change_artifacts(changes_dir, change_name)` — returns a list of `(file_path, artifact_type, name)` tuples by walking `openspec/changes/<name>/`
- [x] 1.3 Implement `_discover_global_specs(specs_dir)` — returns `(file_path, ArtifactType.spec, name)` tuples from `openspec/specs/<capability>/spec.md`
- [x] 1.4 Implement `_build_existing_index(project_id)` — queries all artifacts for the project and returns a `{source_path: artifact}` dict keyed on `metadata["source_path"]`
- [x] 1.5 Implement the main import loop: for each discovered file, skip if in index (unless force), embed content, call `create_artifact` or `update_artifact`
- [x] 1.6 Implement the relationship pass: after all artifacts are upserted, create `depends_on` links per the rules in design.md

## 2. CLI command

- [x] 2.1 Add a Typer app in `cli/import_openspec.py` with command `openspec(path, change, project, force)` — command path becomes `opensddrag import openspec`
- [x] 2.2 Register the new app in `cli/main.py` as `app.add_typer(import_cmd.app, name="import")`
- [x] 2.3 Add rich progress output: per-artifact status lines (imported / skipped / failed) and a summary table at the end

## 3. MCP tool

- [x] 3.1 Add `openspec_import` tool definition to `list_tools()` in `mcp/server.py` with inputs `path`, `change` (optional), `project_slug` (optional), `force` (optional)
- [x] 3.2 Add the `openspec_import` handler in `call_tool()` — call `import_openspec_path()` and return structured JSON result with `imported`, `skipped`, `failed` counts

## 4. Tests

- [x] 4.1 Create `tests/test_import_openspec.py` with a fixture that builds a minimal temporary OpenSpec directory (one change with all four artifact types)
- [x] 4.2 Test happy path: all four artifact types are imported, correct `ArtifactType` assigned, embeddings non-null, `source_path` in metadata
- [x] 4.3 Test idempotency: running import twice produces the same artifact count (second run skips all)
- [x] 4.4 Test `--force`: running with force re-embeds and updates `updated_at`
- [x] 4.5 Test relationship creation: `task` artifact has `depends_on` links to the change's spec and design artifacts
- [x] 4.6 Test global specs: files under `openspec/specs/` are imported with `change_name=None` in metadata
- [x] 4.7 Test `--change` filter: only the named change's artifacts are imported when the flag is provided
- [x] 4.8 Test missing-path error: import on a non-existent path exits with a clear error message

## 5. Documentation

- [x] 5.1 Add `opensddrag import openspec` usage example to the CLI section of `CLAUDE.md`
