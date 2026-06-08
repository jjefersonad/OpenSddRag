### Requirement: CLI command imports OpenSpec documents
The system SHALL provide a CLI command `opensddrag import openspec <path>` that scans a given directory for OpenSpec artifacts and ingests them into the OpenSddRag database as typed, embedded artifacts.

#### Scenario: Import all changes from an OpenSpec project
- **WHEN** the user runs `opensddrag import openspec /path/to/project`
- **THEN** the system discovers all change directories under `openspec/changes/`
- **AND** imports each recognized artifact file (`proposal.md`, `design.md`, `tasks.md`, `specs/**/*.md`) as a corresponding OpenSddRag artifact type
- **AND** reports the count of artifacts imported per change

#### Scenario: Import a single change by name
- **WHEN** the user runs `opensddrag import openspec /path/to/project --change <name>`
- **THEN** only artifacts from `openspec/changes/<name>/` are imported
- **AND** artifacts from other changes are left untouched

#### Scenario: Import global capability specs
- **WHEN** the user runs `opensddrag import openspec /path/to/project`
- **THEN** the system also discovers all spec files under `openspec/specs/`
- **AND** imports each as an artifact of type `spec` with the capability name derived from the directory name

#### Scenario: Idempotent re-run skips existing artifacts
- **WHEN** the user runs the import command a second time on the same path
- **THEN** artifacts that have already been imported (matched by source path) are skipped
- **AND** the command exits successfully with a message indicating how many were skipped

#### Scenario: Force re-import overwrites existing artifacts
- **WHEN** the user runs `opensddrag import openspec /path/to/project --force`
- **THEN** all artifacts are re-imported, overwriting previously ingested versions
- **AND** embeddings are recomputed

#### Scenario: Missing path produces a clear error
- **WHEN** the user provides a path that does not exist or does not contain an `openspec/` directory
- **THEN** the command exits with a non-zero status and a human-readable error message

### Requirement: MCP tool triggers OpenSpec import
The system SHALL expose an MCP tool `openspec_import` that allows agents to import OpenSpec artifacts from within a session, using the same logic as the CLI command.

#### Scenario: Agent imports a project via MCP tool
- **WHEN** an agent calls `openspec_import` with `{"path": "/path/to/project"}`
- **THEN** the tool runs the same discovery and import logic as the CLI
- **AND** returns a structured result with counts of imported, skipped, and failed artifacts

#### Scenario: Agent imports a specific change via MCP tool
- **WHEN** an agent calls `openspec_import` with `{"path": "/path/to/project", "change": "my-change"}`
- **THEN** only the named change's artifacts are imported

### Requirement: Artifact type mapping from OpenSpec to OpenSddRag
The system SHALL map OpenSpec artifact files to OpenSddRag artifact types using the following rules:
- `proposal.md` → type `proposal`
- `design.md` → type `design`
- `tasks.md` → type `tasks`
- `specs/<capability>/spec.md` inside a change directory → type `spec`
- `openspec/specs/<capability>/spec.md` (global) → type `spec`

#### Scenario: Each imported artifact receives the correct type
- **WHEN** any OpenSpec artifact is imported
- **THEN** its `type` field in the database matches the mapping table above

#### Scenario: Artifact name follows OpenSddRag naming convention
- **WHEN** a change-level artifact is imported
- **THEN** its name is set to `<change-name>-<artifact-type>` (e.g., `add-auth-proposal`, `add-auth-design`)
- **AND** a capability spec name is set to `<change-name>-<capability>-spec` (e.g., `add-auth-login-spec`)

#### Scenario: Global spec name uses capability only
- **WHEN** a global spec from `openspec/specs/<capability>/spec.md` is imported
- **THEN** its name is set to `<capability>-spec` (e.g., `auth-login-spec`)

### Requirement: Artifact relationships are preserved
The system SHALL create `artifact_relationships` entries that mirror the dependency order inherent in OpenSpec (proposal → specs/design → tasks).

#### Scenario: Spec depends on its change's proposal
- **WHEN** a spec artifact is imported for a given change
- **THEN** a `depends_on` relationship is created from the spec to the change's proposal artifact (if the proposal was also imported)

#### Scenario: Design depends on proposal
- **WHEN** a design artifact is imported for a given change
- **THEN** a `depends_on` relationship is created from the design to the change's proposal artifact

#### Scenario: Tasks depend on specs and design
- **WHEN** a tasks artifact is imported for a given change
- **THEN** `depends_on` relationships are created from tasks to all spec artifacts of the same change
- **AND** to the design artifact if one was also imported

### Requirement: Imported artifacts receive semantic embeddings
The system SHALL compute and store a 384-dimension embedding for each imported artifact using the existing embedding service.

#### Scenario: Embedding is computed from the full markdown content
- **WHEN** any artifact is imported
- **THEN** its `vector` column is populated using the content of the artifact file
- **AND** the artifact becomes searchable via `opensddrag search semantic`

#### Scenario: Source metadata is stored
- **WHEN** any artifact is imported
- **THEN** the artifact's `metadata` JSON field includes `{"source": "openspec", "source_path": "<relative-path-to-file>", "change_name": "<name>"}`
- **AND** the `source_path` is stored relative to the OpenSpec project root
