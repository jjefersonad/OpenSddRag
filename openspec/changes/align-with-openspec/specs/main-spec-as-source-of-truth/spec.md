## ADDED Requirements

### Requirement: Main spec artifacts serve as the canonical source of truth
The system SHALL maintain a distinct category of spec artifacts — "main specs" — that represent the current, authoritative behavior of the system independent of any in-progress change. A main spec is identified by the absence of `change_name` in its metadata (or `is_delta: false`). Every capability that has been specified at least once SHALL have exactly one main spec artifact per project.

#### Scenario: Main spec created for a new capability
- **WHEN** `/opsr:spec` is called for a capability that has no existing main spec in the database
- **THEN** a new artifact is created with `type="spec"`, `metadata.is_delta=false`, and no `change_name` in metadata

#### Scenario: Delta spec created for a modified capability
- **WHEN** `/opsr:spec` is called for a capability that already has a main spec in the database
- **THEN** a new artifact is created with `type="spec"`, `metadata.is_delta=true`, and `metadata.change_name` set to the current change name

#### Scenario: Main spec updated by sync
- **WHEN** `/opsr:sync` is called for a change that has delta specs
- **THEN** the delta sections (ADDED/MODIFIED/REMOVED/RENAMED) are merged into the corresponding main spec artifact
- **THEN** the main spec content reflects all changes from the delta
- **THEN** the delta spec is marked as `status="archived"`

#### Scenario: Main spec survives archive
- **WHEN** a change is archived via `/opsr:archive`
- **THEN** all delta specs for that change are archived
- **THEN** main specs for the affected capabilities remain with `status="draft"` (active / current)

### Requirement: Main specs are searchable as system state
The system SHALL include main specs in semantic search results when querying without `is_delta` filter, allowing agents to discover existing capability specifications before creating new ones.

#### Scenario: Semantic search returns main spec
- **WHEN** `search_semantic` is called with a query related to an existing capability
- **THEN** the main spec artifact for that capability appears in the results
- **THEN** the result includes `metadata.is_delta=false` to signal it is the canonical version
