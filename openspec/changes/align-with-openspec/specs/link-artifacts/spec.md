## ADDED Requirements

### Requirement: link_artifacts is idempotent
Calling `link_artifacts` with the same `source_name`, `target_name`, and `relationship_type` multiple times SHALL result in exactly one relationship record in the database. Duplicate calls MUST NOT create duplicate rows.

#### Scenario: Second link call returns without creating duplicate
- **WHEN** `link_artifacts(source_name="foo-spec", target_name="foo-proposal", relationship_type="implements")` is called twice in succession
- **THEN** the `artifact_relationships` table contains exactly one row for that combination
- **THEN** the second call succeeds without error

#### Scenario: get_relationships does not return duplicate entries
- **WHEN** `get_relationships` is called after multiple identical `link_artifacts` calls
- **THEN** the returned list contains each related artifact exactly once

### Requirement: UNIQUE constraint enforces deduplication at the database level
A UNIQUE constraint on `(source_id, target_id, relationship_type)` in the `artifact_relationships` table SHALL be the enforcement mechanism, not application-level checks. The `ON CONFLICT DO NOTHING` clause in the INSERT statement SHALL be effective because this constraint exists.

#### Scenario: Database migration adds the UNIQUE constraint
- **WHEN** the migration containing the UNIQUE constraint is applied to a database with existing relationship data
- **THEN** the migration succeeds if no duplicate rows exist
- **THEN** any existing duplicate rows are deduplicated before the constraint is applied (migration handles this)

#### Scenario: ON CONFLICT DO NOTHING returns existing relationship gracefully
- **WHEN** `link_artifacts` is called for an already-existing relationship
- **THEN** no error is raised
- **THEN** the function returns successfully (even if RETURNING * yields no row on conflict)
