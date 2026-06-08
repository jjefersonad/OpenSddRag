## Why

When the Node.js client (`opensddrag init`) tries to create a new project via `POST /api/projects`, Starlette returns a 405 Method Not Allowed because the route list has two separate `Route` objects with the same path but different methods — Starlette matches the first one (GET-only) and rejects the POST without checking the second route. This blocks any user trying to connect a new project to the MCP server.

## What Changes

- Merge the two separate `Route("/api/projects", ...)` entries (one for GET, one for POST) into a single route handler that dispatches internally based on the HTTP method.
- The merged handler accepts both `GET` and `POST` on `/api/projects`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sse-http-routing`: The Starlette routing configuration in `_main_sse` is corrected to properly handle multiple HTTP methods on the same path.

## Impact

- `mcp-server/src/opensddrag/mcp/server.py` — `_main_sse` function: merge the duplicate `/api/projects` routes.
- No API contract changes; behavior for valid GET and POST requests is identical.
- No breaking changes.
