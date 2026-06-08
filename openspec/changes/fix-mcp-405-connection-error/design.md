## Context

The MCP server exposes a REST API alongside the SSE/MCP endpoint for use by the Node.js client. The `/api/projects` endpoint must support both `GET` (list projects) and `POST` (create project). Currently the Starlette router has two separate `Route` objects for the same path:

```python
Route("/api/projects", endpoint=api_list_projects, methods=["GET"]),
Route("/api/projects", endpoint=api_create_project, methods=["POST"]),
```

Starlette's router evaluates routes in order. When a `POST` arrives, it matches the first route (path matches), sees the method is not allowed, and immediately returns `405` without checking the next route. This means `POST /api/projects` always fails.

Affected file: `mcp-server/src/opensddrag/mcp/server.py`, function `_main_sse`.

## Goals / Non-Goals

**Goals:**
- Fix `POST /api/projects` returning 405 when the server is running.
- Keep the existing API contract (same request/response shapes).

**Non-Goals:**
- Adding authentication or CORS support.
- Changing the client code.
- Adding new endpoints.

## Decisions

### Decision: Single dispatching handler over two separate routes

**Chosen:** Merge `api_list_projects` and `api_create_project` into a single `api_projects` handler that checks `request.method` and dispatches internally. Register it as one route with `methods=["GET", "POST"]`.

**Alternative considered:** Use Starlette's `Router` with separate route entries per method — rejected because Starlette's `Route` object is still order-dependent, and the same 405 bug reappears if the first match wins without method-awareness.

**Alternative considered:** Separate URL paths (e.g., `GET /api/projects` and `POST /api/projects/create`) — rejected because it would be a breaking API change.

The dispatching handler is the minimal, correct fix that respects Starlette's routing model.

## Risks / Trade-offs

- [Risk: merge adds indirection] → Mitigation: the dispatch is a single `if/elif` block; the existing handler functions remain intact and are called as before, so logic is not duplicated.
- [Risk: other routes with same pattern] → No other routes in `_main_sse` share a path with multiple methods, so this is an isolated fix.

## Migration Plan

1. Edit `_main_sse` in `mcp-server/src/opensddrag/mcp/server.py`.
2. Add a new `api_projects` dispatcher function.
3. Replace the two separate `Route("/api/projects", ...)` entries with one `Route("/api/projects", endpoint=api_projects, methods=["GET", "POST"])`.
4. Restart the Docker container (`docker compose restart mcp-server` or `docker compose up -d`).
5. Verify with: `curl -X POST http://localhost:8000/api/projects -H "Content-Type: application/json" -d '{"slug":"test","name":"Test"}'` — should return 200 or 201, not 405.

Rollback: revert the single edited file and restart the container.
