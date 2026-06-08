## ADDED Requirements

### Requirement: API key creation
The system SHALL allow an administrator to create an API key via the CLI. Each key SHALL be associated with either a specific project slug or have global scope. The created key SHALL be displayed once in plaintext at creation time and never retrievable in plaintext again. The key SHALL be stored as a SHA-256 hash with a unique salt in the `api_keys` table.

#### Scenario: Create a project-scoped key
- **WHEN** the administrator runs `opensddrag key create --project <slug> --description "dev key"`
- **THEN** the system generates a random 32-byte key, hashes it, stores the hash, and prints the plaintext key exactly once

#### Scenario: Create a global key
- **WHEN** the administrator runs `opensddrag key create --description "global key"` without `--project`
- **THEN** the system creates a key with `project_id = NULL` that grants access to all projects

#### Scenario: Create a key with expiry
- **WHEN** the administrator includes `--expires-at "2026-12-31"`
- **THEN** the key is stored with an `expires_at` timestamp and SHALL be rejected after that date

### Requirement: API key listing
The system SHALL allow listing all API keys (active and revoked) via the CLI. The listing SHALL show key ID, prefix (first 8 characters of the raw key for identification), description, project scope, creation date, expiry, and revocation status. Plaintext keys SHALL NOT appear in the listing.

#### Scenario: List all keys
- **WHEN** the administrator runs `opensddrag key list`
- **THEN** the system prints a table with all keys, never showing the full key value

#### Scenario: List keys for a project
- **WHEN** the administrator runs `opensddrag key list --project <slug>`
- **THEN** only keys scoped to that project (or global keys) are shown

### Requirement: API key revocation
The system SHALL allow revoking an API key by its ID. Revoked keys SHALL be kept in the database for audit purposes but SHALL be rejected by the auth middleware. Revocation SHALL be immediate and irreversible via the CLI.

#### Scenario: Revoke a key
- **WHEN** the administrator runs `opensddrag key revoke <key-id>`
- **THEN** the key's `revoked_at` field is set to the current timestamp and subsequent requests with that key return 401

#### Scenario: Revoke an already-revoked key
- **WHEN** the administrator tries to revoke a key that is already revoked
- **THEN** the system SHALL display a warning but return success (idempotent)

### Requirement: API keys database schema
The system SHALL maintain an `api_keys` table with the following columns: `id` (UUID primary key), `key_hash` (text, the SHA-256 hex digest), `key_prefix` (text, first 8 chars of raw key), `description` (text), `project_id` (UUID nullable FK to `projects`), `created_at` (timestamptz), `expires_at` (timestamptz nullable), `revoked_at` (timestamptz nullable). An index SHALL exist on `key_hash` for fast lookup.

#### Scenario: Hash collision resistance
- **WHEN** two different plaintext keys are stored
- **THEN** their `key_hash` values SHALL be distinct (SHA-256 collision probability is negligible)

#### Scenario: Key lookup performance
- **WHEN** the middleware looks up a key by hash on each request
- **THEN** the lookup SHALL use the `key_hash` index and complete in O(log n) time
