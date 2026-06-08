## 1. Fix Starlette Routing

- [x] 1.1 In `mcp-server/src/opensddrag/mcp/server.py`, inside `_main_sse`, add a new `api_projects` dispatcher function that calls `api_list_projects` for GET and `api_create_project` for POST
- [x] 1.2 Replace the two separate `Route("/api/projects", ...)` entries with a single `Route("/api/projects", endpoint=api_projects, methods=["GET", "POST"])`

## 2. Verify the Fix

- [x] 2.1 Restart the MCP server (`docker compose up -d` or local `opensddrag server start --transport sse`)
- [x] 2.2 Run `curl -X POST http://localhost:8000/api/projects -H "Content-Type: application/json" -d '{"slug":"smoke-test","name":"Smoke Test"}'` and confirm HTTP 201 (not 405)
- [x] 2.3 Run `curl http://localhost:8000/api/projects` and confirm HTTP 200 with a JSON array containing the created project
- [x] 2.4 Run `node bin/opensddrag.js init` from a test project directory and confirm it completes without a 405 error
