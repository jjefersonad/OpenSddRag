## Why

The OpenSddRag MCP server currently runs with no authentication — any client with network access can read and write artifacts, projects, and traces. To safely expose it online for multiple developers, we need API key-based authorization that controls who can connect and which project they operate in.

## What Changes

- Add an `api_keys` database table to store hashed API keys tied to projects (or global)
- Add auth middleware to the Starlette HTTP/SSE app that validates `Authorization: Bearer <key>` on every request
- Add `opensddrag key create/list/revoke` CLI commands to manage API keys
- Update `config.py` to support an `AUTH_ENABLED` flag (default `true` in SSE mode, `false` in stdio mode)
- Update the Node.js client `init` command to accept and store an API key for authenticated connections
- Document the API key workflow in the project README

## Capabilities

### New Capabilities

- `api-key-management`: CRUD operations for API keys — create (with optional expiry and project scope), list, and revoke keys stored hashed in PostgreSQL
- `auth-middleware`: Starlette middleware that intercepts all HTTP requests in SSE mode, validates the Bearer token against stored keys, and returns 401/403 for invalid or expired keys; stdio transport bypasses auth entirely

### Modified Capabilities

*(none — no existing spec-level behavior changes)*

## Impact

- **`mcp-server/src/opensddrag/db/migrations/`** — new migration adds `api_keys` table
- **`mcp-server/src/opensddrag/db/`** — new `api_key_repository.py` for key CRUD
- **`mcp-server/src/opensddrag/mcp/server.py`** — wire auth middleware into Starlette app in SSE mode
- **`mcp-server/src/opensddrag/config.py`** — add `AUTH_ENABLED`, `AUTH_BYPASS_IPS` settings
- **`mcp-server/src/opensddrag/cli/main.py`** — add `key` sub-command group
- **`client/`** — pass `Authorization` header when connecting to SSE server; `init` prompts for API key
- **Dependencies** — `passlib` or `hashlib` (stdlib) for key hashing; no heavy auth framework needed
