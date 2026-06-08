## ADDED Requirements

### Requirement: update_artifact merges metadata instead of replacing it
The `update_artifact` MCP tool and its underlying repository function SHALL perform a JSONB merge when updating the `metadata` field of an artifact. Existing metadata keys not present in the update payload MUST be preserved. This prevents data loss when updating only `status` (e.g., during archive) after the artifact already has metadata keys like `is_delta`, `capability`, or `change_name`.

#### Scenario: Archiving a spec preserves is_delta and capability
- **WHEN** `update_artifact` is called with `status="archived"` and `metadata={"archived_at": "...", "change_name": "..."}` on a spec that has `metadata.is_delta=true` and `metadata.capability="auth"`
- **THEN** the stored metadata contains `is_delta=true`, `capability="auth"`, `archived_at`, and `change_name`
- **THEN** no prior metadata keys are lost

#### Scenario: Updating only status does not touch metadata
- **WHEN** `update_artifact` is called with only `status="active"` and no `metadata` field
- **THEN** the existing metadata is unchanged

#### Scenario: Explicit null clears a metadata key
- **WHEN** `update_artifact` is called with `metadata={"deprecated_key": null}`
- **THEN** `deprecated_key` is removed from the stored metadata
- **THEN** all other existing metadata keys are preserved

### Requirement: Repository merge is implemented at the SQL level
The merge SHALL be implemented using PostgreSQL's `||` JSONB concatenation operator (or `jsonb_strip_nulls` for null-removal), not in Python, to ensure atomicity and avoid race conditions.

#### Scenario: Concurrent updates do not corrupt metadata
- **WHEN** two concurrent calls update different metadata keys on the same artifact
- **THEN** both keys are present in the final metadata
- **THEN** no key is silently overwritten by the other update
