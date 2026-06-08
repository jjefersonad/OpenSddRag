## ADDED Requirements

### Requirement: ArtifactType enum does not include the unused change type
The `change` value SHALL be removed from `ArtifactType` in the Python model, the PostgreSQL ENUM, and the MCP tool `inputSchema` definitions. No command or tool uses this type; its presence causes confusion when AI models enumerate available artifact types.

#### Scenario: create_artifact rejects type=change after removal
- **WHEN** `create_artifact` is called with `type="change"`
- **THEN** the MCP server returns a validation error
- **THEN** no artifact is created

#### Scenario: list_artifacts and search_semantic do not offer change as a filter
- **WHEN** the list of valid type values is exposed to the model (via inputSchema)
- **THEN** `"change"` is not present in the enum array
- **THEN** valid types are: `["proposal", "spec", "task", "design"]`

### Requirement: Existing data is not broken by the type removal
If any artifact with `type="change"` exists in a database before the migration, the migration SHALL handle the removal gracefully.

#### Scenario: Migration fails safely if change-type artifacts exist
- **WHEN** the migration to alter the ENUM runs on a database that contains rows with `type="change"`
- **THEN** the migration reports an error and does not proceed
- **THEN** a data cleanup step (documented in migration notes) must be run first

#### Scenario: Clean database migrates without issues
- **WHEN** the migration runs on a database with no `type="change"` artifacts
- **THEN** the ENUM is altered successfully
- **THEN** all existing artifact types (proposal, spec, task, design) continue to work
