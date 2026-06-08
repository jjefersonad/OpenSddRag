## 1. Database

- [x] 1.1 Create `mcp-server/src/opensddrag/db/migrations/002_api_keys.sql` with the `api_keys` table (id UUID PK, key_hash text, key_prefix text, description text, project_id UUID nullable FK, created_at timestamptz, expires_at timestamptz nullable, revoked_at timestamptz nullable) and an index on `key_hash`
- [x] 1.2 Apply the migration by running `opensddrag init` (or directly via `psql`) and verify the table exists

## 2. API Key Repository

- [x] 2.1 Create `mcp-server/src/opensddrag/db/api_key_repository.py` with `ApiKeyRepository` class
- [x] 2.2 Implement `create_key(description, project_id, expires_at)` — generates 32-byte random key, computes SHA-256 hash, stores row, returns plaintext key (once)
- [x] 2.3 Implement `list_keys(project_id=None)` — returns all keys (active and revoked), optionally filtered by project
- [x] 2.4 Implement `revoke_key(key_id)` — sets `revoked_at = NOW()` if not already set
- [x] 2.5 Implement `lookup_by_hash(key_hash)` — returns the key row or None; used by middleware on each request

## 3. Config

- [x] 3.1 Add `auth_enabled: bool = True` field to `Settings` in `config.py` (reads `AUTH_ENABLED` env var)

## 4. Auth Middleware

- [x] 4.1 Create `mcp-server/src/opensddrag/mcp/auth.py` with `AuthMiddleware(BaseHTTPMiddleware)`
- [x] 4.2 Implement `dispatch()`: extract `Authorization: Bearer <token>`, compute SHA-256 hash, call `lookup_by_hash`
- [x] 4.3 Return HTTP 401 JSON if header is missing, key not found, key revoked, or key expired
- [x] 4.4 Return HTTP 403 JSON if key is project-scoped and the resolved project doesn't match `X-Project` header
- [x] 4.5 On success, set `request.state.project_slug` and call `await call_next(request)`
- [x] 4.6 For global keys with no `X-Project` header, fall back to `settings.opensddrag_project`

## 5. Wire Middleware into SSE Server

- [x] 5.1 In `_main_sse()` in `server.py`, conditionally add `AuthMiddleware` to the Starlette app when `settings.auth_enabled` is `True`
- [x] 5.2 Log `WARNING: Auth is disabled. Do not expose this server publicly.` at startup when `auth_enabled=False`

## 6. CLI Key Commands

- [x] 6.1 Create `mcp-server/src/opensddrag/cli/keys.py` with a Typer app (`keys_app`)
- [x] 6.2 Implement `key create` command: accepts `--project`, `--description`, `--expires-at`; prints generated key with a prominent "Save this key — it will not be shown again" warning
- [x] 6.3 Implement `key list` command: accepts `--project`; prints a table (id, prefix, description, project, created_at, expires_at, status)
- [x] 6.4 Implement `key revoke` command: accepts `<key-id>`; sets revoked_at and prints confirmation
- [x] 6.5 Register `keys_app` in `cli/main.py` with `app.add_typer(keys_app, name="key")`

## 7. Node.js Client Update

- [x] 7.1 Update `client/bin/opensddrag.js init` to prompt for an API key when `--server` is provided
- [x] 7.2 Write the API key to the generated `.mcp.json` as a header: `"headers": {"Authorization": "Bearer <key>"}`

## 8. Tests

- [x] 8.1 Write unit tests for `ApiKeyRepository`: create, list, revoke, lookup valid/expired/revoked keys
- [x] 8.2 Write integration tests for `AuthMiddleware`: missing header → 401, invalid key → 401, expired key → 401, wrong project → 403, valid key → 200
- [x] 8.3 Write a test that verifies stdio transport starts without auth middleware loaded

## 9. Documentation

- [x] 9.1 Update `mcp-server/.env.example` to include `AUTH_ENABLED=true` with a comment
- [x] 9.2 Add an "Authorization" section to the project README explaining how to create keys and configure the client
