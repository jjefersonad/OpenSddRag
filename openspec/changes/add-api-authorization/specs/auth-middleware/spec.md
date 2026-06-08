## ADDED Requirements

### Requirement: Bearer token validation on HTTP requests
The system SHALL validate an `Authorization: Bearer <key>` header on every inbound HTTP request when running in SSE/HTTP transport mode. If the header is absent or the token is invalid, the system SHALL return HTTP 401. If the token is valid but does not have permission for the requested project, the system SHALL return HTTP 403.

#### Scenario: Valid key is accepted
- **WHEN** a client sends a request with `Authorization: Bearer <valid-key>`
- **THEN** the middleware resolves the key's project scope and forwards the request to the MCP handler

#### Scenario: Missing Authorization header
- **WHEN** a client sends a request with no `Authorization` header
- **THEN** the middleware returns HTTP 401 with body `{"error": "missing authorization header"}`

#### Scenario: Invalid or revoked key
- **WHEN** a client sends a request with an unrecognized or revoked key
- **THEN** the middleware returns HTTP 401 with body `{"error": "invalid or revoked api key"}`

#### Scenario: Expired key
- **WHEN** a client sends a request with a key whose `expires_at` is in the past
- **THEN** the middleware returns HTTP 401 with body `{"error": "api key expired"}`

#### Scenario: Key scoped to wrong project
- **WHEN** a client sends a request with a project-scoped key and the request targets a different project
- **THEN** the middleware returns HTTP 403 with body `{"error": "api key not authorized for this project"}`

### Requirement: Auth bypass in stdio transport
The system SHALL NOT enforce API key validation when running in stdio transport mode (local Claude Code spawn). Auth is irrelevant for local-only stdio connections and SHALL be skipped entirely to avoid friction for local development.

#### Scenario: Stdio transport ignores auth
- **WHEN** the server is started with `opensddrag server start` (stdio, no `--transport sse`)
- **THEN** no auth middleware is loaded and all MCP tool calls proceed without token validation

### Requirement: Auth can be disabled via config
The system SHALL support an `AUTH_ENABLED=false` environment variable that disables the auth middleware even in SSE mode. This is intended for development and trusted internal deployments. When disabled, the server SHALL log a prominent warning at startup.

#### Scenario: Auth disabled via env var
- **WHEN** `AUTH_ENABLED=false` is set and the server starts in SSE mode
- **THEN** all requests are accepted without a token and a warning line is logged: `WARNING: Auth is disabled. Do not expose this server publicly.`

#### Scenario: Auth enabled by default
- **WHEN** `AUTH_ENABLED` is not set and the server starts in SSE mode
- **THEN** the auth middleware is active and all unauthenticated requests are rejected

### Requirement: Project context injection from key
The system SHALL inject the resolved project slug into the request context after successful authentication, so downstream MCP tool handlers can use the key's project scope without re-querying.

#### Scenario: Global key sets project from request
- **WHEN** a global API key is used and the request includes an `X-Project` header
- **THEN** the middleware injects that project slug as the active project context

#### Scenario: Project-scoped key overrides request project
- **WHEN** a project-scoped API key is used
- **THEN** the middleware injects the key's own project slug regardless of any `X-Project` header, and any mismatch results in HTTP 403
