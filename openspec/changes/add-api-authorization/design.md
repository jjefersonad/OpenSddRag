## Context

OpenSddRag's MCP server runs in two transport modes:

- **stdio** — spawned locally by Claude Code; trust is implicit (same machine)
- **SSE/HTTP** — Starlette app listening on a port; the only mode that can be exposed online

Currently the Starlette app (`_main_sse`) mounts a single `/mcp` route with no authentication. Adding auth only to the SSE path keeps the stdio workflow frictionless while protecting the public endpoint.

The database already has a `projects` table with UUID primary keys. API keys will be a lightweight addition: a new migration, a new repository, and a Starlette middleware.

No external auth service (OAuth, JWT, etc.) is needed — API keys are the right primitive for developer-to-developer access where the consumer is a tool (Claude Code), not an end user with a browser.

## Goals / Non-Goals

**Goals:**
- Protect the SSE/HTTP endpoint with Bearer token auth
- Provide CLI commands to create, list, and revoke API keys
- Allow keys to be scoped to a project or global
- Support key expiry
- Keep stdio transport completely unchanged
- Allow auth to be disabled via env var for trusted internal deployments

**Non-Goals:**
- OAuth 2.0 / OIDC flows
- Role-based access control (RBAC) — keys are binary: valid or not
- Rate limiting per key (separate concern)
- Key rotation automation
- Web UI for key management

## Decisions

### Decision 1: SHA-256 for key hashing (not bcrypt/argon2)

API keys are long, high-entropy random strings (32 bytes → 256 bits), not user-created passwords. SHA-256 is sufficient: there is no dictionary attack vector because the input space is 2²⁵⁶. bcrypt adds 100–300 ms per request with no security gain for random keys. Using `hashlib.sha256` from the Python stdlib avoids a new dependency.

**Alternative considered**: `passlib` with bcrypt — rejected because per-request latency is unacceptable for a tool-to-tool API.

### Decision 2: Starlette Middleware class for auth

The auth check wraps the entire Starlette app using a standard ASGI middleware (`starlette.middleware.base.BaseHTTPMiddleware`). This intercepts all routes, including `/mcp`, before any handler runs.

**Alternative considered**: Per-route dependency injection — rejected because Starlette's routing model with `Mount` makes it harder to inject per-route logic cleanly, and the middleware pattern is idiomatic for cross-cutting concerns.

### Decision 3: Project context propagated via `request.state`

After a successful key validation, the middleware sets `request.state.project_slug`. The MCP session manager receives the ASGI scope, so the project can be injected into the scope's `state` dict and read by tool handlers downstream.

**Alternative considered**: Thread-local / context var — rejected because Starlette already provides `request.state` for exactly this purpose.

### Decision 4: New migration file `002_api_keys.sql`

The `api_keys` table is additive — no changes to existing tables. A new migration file keeps the history clean. The migration runner in `connection.py` already applies all `.sql` files in order.

### Decision 5: `opensddrag key` CLI sub-command group

The new `key` command group (`create`, `list`, `revoke`) mirrors the existing pattern (`opensddrag project`, `opensddrag spec`, etc.) using Typer sub-apps.

## Implementation Map

```
mcp-server/
  src/opensddrag/
    config.py                    ← add AUTH_ENABLED (bool, default True)
    db/
      migrations/
        002_api_keys.sql         ← new table
      api_key_repository.py      ← create / list / revoke / lookup_by_hash
    mcp/
      auth.py                    ← AuthMiddleware (BaseHTTPMiddleware)
      server.py                  ← wire middleware into _main_sse()
    cli/
      keys.py                    ← Typer app: create / list / revoke
      main.py                    ← add `app.add_typer(keys_app, name="key")`
```

## Risks / Trade-offs

- **Key leakage on creation** — The plaintext key is shown once in the terminal. If the administrator scrolls away, the key is lost and a new one must be created. Mitigation: print the key prominently with a clear warning; provide a simple `opensddrag key create` copy-paste workflow.

- **SHA-256 with no salt** — Since keys are random, salting adds no security. However, if a database dump leaks, an attacker who knows the raw key format can verify a guessed key. Mitigation: document that keys should be treated like passwords (never committed, stored in secrets managers).

- **`AUTH_ENABLED=false` footgun** — If accidentally left off in production, the server is open. Mitigation: the server logs a prominent `WARNING` at startup and the default is `AUTH_ENABLED=true`.

- **MCP session manager scope** — The `StreamableHTTPSessionManager` manages WebSocket/SSE sessions; injecting project context into its scope requires verifying that `request.state` survives into the session handler. This needs a quick integration test. If it doesn't propagate, a fallback is to encode the project slug in a custom header that the MCP tool handlers read directly from the environment.

## Migration Plan

1. Run `opensddrag init` (or manually apply `002_api_keys.sql`) on the target database
2. Generate at least one API key per project: `opensddrag key create --project <slug>`
3. Set `AUTH_ENABLED=true` (default) and restart the SSE server
4. Update any existing Claude Code `.mcp.json` configs to include the API key header
5. Rollback: set `AUTH_ENABLED=false` to disable auth without dropping the table

## Open Questions

1. Should the Node.js `client init` command prompt for an API key and write it to `.mcp.json` automatically, or leave it for the developer to add manually? (Recommended: auto-prompt for better DX)
2. Should global keys inject a default project from the `OPENSDDRAG_PROJECT` env var, or require an `X-Project` header? (Recommended: fall back to `OPENSDDRAG_PROJECT` if no header is provided)
