# Clean Architecture — mcp-server

## Layer diagram

```
┌─────────────────────────────────────────────────────────┐
│  mcp/  (MCP adapter)                                    │
│  MCPServerAdapter → call_tool → execute_tool.execute()  │
└────────────────────────┬────────────────────────────────┘
                         │ depends on
┌────────────────────────▼────────────────────────────────┐
│  core/usecases/   (application logic)                   │
│  ExecuteToolUseCase, ListToolsUseCase                   │
└──────────┬────────────────────────────┬─────────────────┘
           │ depends on                 │ depends on
┌──────────▼──────────┐    ┌───────────▼─────────────────┐
│  core/domain/       │    │  core/ports/  (protocols)   │
│  pure Python types  │◄───│  ToolRegistry, RateLimiter  │
│  no side effects    │    │  Authenticator, Executor    │
└─────────────────────┘    └───────────▲─────────────────┘
                                       │ implements
                         ┌─────────────┴─────────────────┐
                         │  infrastructure/               │
                         │  PgToolRegistry, PgRateLimiter │
                         │  PgToolExecutor, composition   │
                         └───────────────────────────────┘
```

**Dependency rule**: arrows point inward only. `core/` never imports `infrastructure/`, `mcp/`, or `db/`.

## Decision table: where do I put new code?

| I want to…                             | Put it in…                                             |
|----------------------------------------|--------------------------------------------------------|
| Add a business rule or domain type     | `core/domain/` — pure Python, no I/O                  |
| Add a new tool to the MCP server       | Register in `PgToolRegistry`; add executor function in `infrastructure/pg/tool_executors.py` |
| Add a new persistence backend          | New directory `infrastructure/<backend>/`, implement the port from `core/ports/` |
| Change or add an MCP transport         | New file in `mcp/` (stdio) or `rest/` (HTTP REST, future) |
| Add auth or rate-limit policy          | New implementation of `Authenticator`/`RateLimiter` in `infrastructure/` |

## Spec references (opensddrag artifacts)

The design decisions behind this layout are captured in six planning artifacts. Search them via `search_semantic` or `read_artifact(name=..., project_slug="opensddrag")`:

1. `apply-clean-architecture-to-mcp-server-mcp-domain-core-spec` — domain purity rules
2. `apply-clean-architecture-to-mcp-server-tool-execution-usecase-spec` — ExecuteToolUseCase contract
3. `apply-clean-architecture-to-mcp-server-tool-listing-usecase-spec` — ListToolsUseCase contract
4. `apply-clean-architecture-to-mcp-server-mcp-protocol-adapter-spec` — MCPServerAdapter protocol
5. `apply-clean-architecture-to-mcp-server-mcp-infrastructure-spec` — infrastructure adapters
6. `apply-clean-architecture-to-mcp-server-mcp-server-internals-spec` — layer boundary rules (REQ-008–010)
