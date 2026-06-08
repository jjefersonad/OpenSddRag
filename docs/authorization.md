# Authorization

When running OpenSddRag in SSE/HTTP mode for online access, API key authorization is enabled by default.

## How it works

- The SSE server validates `Authorization: Bearer <key>` on every incoming request.
- Keys are stored as SHA-256 hashes in the `api_keys` table.
- Keys can be scoped to a specific project or global (access to all projects).
- stdio transport (local Claude Code) bypasses auth entirely.

## Manage keys

All key management is done via the `opensddrag key` CLI from inside `mcp-server/`:

```bash
# Create a global key
opensddrag key create --description "my dev key"

# Create a key scoped to a project
opensddrag key create --project myproject --description "ci key"

# Create a key with expiry
opensddrag key create --description "temp key" --expires-at "2026-12-31"

# List all keys
opensddrag key list

# Revoke a key
opensddrag key revoke <key-id>
```

The plaintext key is shown **once** at creation time. Save it immediately.

## Connect a project with a key

When running `opensddrag init` against a remote server, you will be prompted for an API key:

```bash
opensddrag init --server https://your-server.example.com
# → prompts for API key
```

Or pass it directly:

```bash
opensddrag init --server https://your-server.example.com --api-key <key>
```

The key is written to `.mcp.json`:

```json
{
  "mcpServers": {
    "opensddrag": {
      "type": "http",
      "url": "https://your-server.example.com/mcp",
      "headers": {
        "Authorization": "Bearer <key>"
      }
    }
  }
}
```

## Disable auth (development only)

Set `AUTH_ENABLED=false` in your `.env` to disable auth for trusted internal deployments:

```env
AUTH_ENABLED=false
```

The server will log a prominent warning at startup. **Never expose an auth-disabled server publicly.**

## Apply pending migrations

After pulling new code, run:

```bash
opensddrag migrate
```

This applies any pending migration files (tracked via `schema_migrations` table) without re-running already-applied ones.
