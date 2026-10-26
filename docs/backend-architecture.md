# Backend Architecture

Technical reference for the `mcp-server/` application — MCP, REST and CLI servers in Python (modular monolith).
Architecture based on Sebastian Buczyński's **Modular Monolith** pattern ([breadcrumbscollector.tech/modular-monolith-in-python](https://breadcrumbscollector.tech/modular-monolith-in-python/)) and Clean Architecture.
For build commands, ports and environment variables, refer to [`CLAUDE.md`](../CLAUDE.md).

---

## Stack

| Technology | Role |
|---|---|
| Python 3.12+ | Server language |
| MCP SDK (`mcp.*`) | MCP protocol (tools/resources) |
| Starlette + Uvicorn | HTTP/SSE transport and app mounting |
| Typer | Administration CLI |
| psycopg (async pool) | PostgreSQL access |
| PostgreSQL + pgvector | Persistence + vector search (HNSW, 384 dims) |
| sentence-transformers | Embedding generation (`all-MiniLM-L6-v2`) |
| pydantic / pydantic-settings | Domain models and `.env`-based configuration |

---

## Principle: modular monolith (modulith)

The server is **a single deployable with deliberately separated components** — not a distributed microservice and not a big ball of mud. Each component (concept from the article):

- Has an **explicit public API** (use cases, facades) and **private details** that no other layer touches (component-level encapsulation).
- Communicates with other components only through **direct calls to the public API** or through **ports (interfaces)** — never importing another component's internals.
- Exposes **DTOs** (`Request`, `Response`), never database models or domain entities, across its boundary.
- Can have **its own internal architecture**: the core component uses Clean Architecture; the data-access components use the simpler repository pattern. The article recommends limiting to 2 internal architectures — which is exactly what we do.

**Why not microservices?** The architectural drivers for distributing (independent scaling, distinct languages, risk isolation) do not apply: this is a single-user, single-deploy tool with a single database. The modulith gives logical separation without the operational cost; if it ever needs to become a service, the boundaries already exist and the price of getting them wrong was low.

---

## Directory Structure

```
mcp-server/src/opensddrag/
├── core/                       # Central component — Clean Architecture
│   ├── domain/                 # Entities and pure rules (Tool, Permission, Response, Request, validation, errors)
│   ├── ports/                  # Interfaces (typing.Protocol) — the only "seam" between use cases and adapters
│   └── usecases/               # Use cases (ExecuteToolUseCase, ListToolsUseCase) — the core's public API
├── infrastructure/             # Concrete adapters of the core ports
│   ├── composition.py          # Composition root — the ONLY module that imports core + infrastructure + db
│   ├── bootstrap.py            # Lifecycle (startup/shutdown of the pool and adapters)
│   ├── auth/                   # NoopAuthenticator, DefaultAuthorizationPolicy
│   ├── memory/                 # In-memory rate limiter and tool registry
│   ├── pg/                     # PostgreSQL adapters (registry, rate limiter, logger, tool_executors)
│   ├── validation/             # JsonSchemaValidator (input and output)
│   └── mcp_resources.py        # MCP resources (projects and artifacts)
├── mcp/                        # MCP transport adapter (protocol) — server.py, auth.py, context.py
├── cli/                        # CLI delivery adapter (typer) — wires sub-typers by domain
├── db/                         # Data layer — async pool, migrations, repositories per aggregate
├── embedding/                  # Embedding service (sentence-transformers)
├── models/                     # Pydantic models of the persisted entities
├── config.py                   # pydantic-settings (env vars / .env)
└── tests/architecture/         # Architecture tests that enforce the import rules
```

---

## Layers and Responsibilities

```
┌──────────────────────────────────────────────────────────────┐
│  mcp/                    DELIVERY ADAPTERS (interfaces)       │
│  cli/                    MCP protocol and typer CLI           │
│  ─ no business rules, only serialization/resolution           │
└──────────────────────────────┬───────────────────────────────┘
                               │ call (the only path)
┌──────────────────────────────▼───────────────────────────────┐
│  core/usecases           CORE PUBLIC API                      │
│  ExecuteToolUseCase      pipeline: auth → rate-limit →        │
│  ListToolsUseCase        validate → execute → log             │
└──────────────────────────────┬───────────────────────────────┘
                               │ depend on interfaces (DIP)
┌──────────────────────────────▼───────────────────────────────┐
│  core/ports              Ports (typing.Protocol, zero impls)  │
│  core/domain             Pure domain (DTOs, Permission, Tool)│
└──────────────────────────────▲───────────────────────────────┘
                               │ implement the ports (DIP)
┌──────────────────────────────┴───────────────────────────────┐
│  infrastructure/         Concrete adapters                    │
│  db/                     Repositories + pool + migrations      │
│  embedding/              Embedding service                    │
└──────────────────────────────────────────────────────────────┘
```

**Dependency rule (the Dependency Rule):** dependencies point Inward/Toward the core. `mcp/` and `cli/` depend on `core/`; `core/` depends only on `core/domain` + `core/ports`; `infrastructure/` and `db/` implement `core/ports` (dependency inversion) — never the other way around.

**What each architecture test enforces (`tests/architecture/test_imports.py`):**

| Test | Rule |
|---|---|
| `test_domain_is_pure` | `core/domain` imports nothing from infra/transport |
| `test_usecases_have_no_infra_or_db_imports` | `core/usecases` does not import `infrastructure/`, `db/` or transport |
| `test_infrastructure_only_imports_downward` | `infrastructure/` never imports from `mcp/`, `cli/` (composition root is exempt) |
| `test_mcp_adapter_does_not_import_repositories` | transport never talks to `db/` — only to use cases |

---

## The Ports (core interfaces)

All in `core/ports/`, defined as `typing.Protocol` — **with no implementations at all**

| Port | Responsibility |
|---|---|
| `ToolRegistryPort` | Registration/lookup of available tools |
| `ToolExecutorPort` | Execution of a tool's body by dispatcher (by `tool.name`) |
| `AuthenticationPort` | Authentication of the `Caller` |
| `AuthorizationPolicyPort` | Call permission per role/permission |
| `RateLimiterPort` | Quota per time window |
| `InputValidatorPort / OutputValidatorPort` | JSON Schema validation (input/output) |
| `LoggerPort` | Structured logging |

The use case never knows whether there is PostgreSQL, memory or JSON Schema behind a port: it uses only the interfaces. This is the article's "direct call via abstract class" (payments vs auctioning platform).

---

## Composition Root — `infrastructure/composition.py`

The single assembly point (equivalent to the article's `main` module): builds all adapters and injects them into the use cases.

- `UseCases` — **frozen** dataclass with the use cases + shared adapters (registry, authenticator, rate limiter, logger). Immutable at runtime; nobody re-wires a port at runtime.
- `build_use_cases(settings, *, tool_executors)` — resolves the adapters automatically by mode (selection criterion):

| Condition | Selected adapters |
|---|---|
| `DATABASE_URL` set **and** `RATE_LIMITER != "memory"` | PostgreSQL (pg_registry, pg_rate_limiter, pg_logger) |
| `DATABASE_URL` empty **or** `RATE_LIMITER=memory` | In-memory (in_memory_registry, in_memory_rate_limiter) |

- `_MappingToolExecutor` — dispatcher that selects the tool's executor by `tool.name`. Tools without an executor fail **loudly with a structured error** (`INTERNAL`), never silently with `None`.
- **The single exception to the linear dependency:** `composition.py` imports from `core/`, `infrastructure/` and `db/` simultaneously. It is the apex of the graph, so it cannot have cycles — and it is explicitly exempted in the architecture test.
- **Lifecycle with `bootstrap.py`** — idempotent startup (connection pool + adapter warm-up) and shutdown, called by the delivery adapters (`_main_stdio`, `_main_sse`).

---

## MCP Protocol Adapter — `mcp/server.py`

Delivery component exposing 23 tools. It contains no business logic:

1. `_resolve_caller()` — extracts the project slug from the MCP context and builds the `Caller` (DTO) with `Permission.ADMIN`.
2. `MCPServerAdapter.call_tool()` → `execute_tool.execute()` (the use case).
3. `_serialize_response()` — serializes `Response` into `TextContent` JSON. Errors become the structured envelope `{"error": {"code": ..., "message": ...}}`, never `None`.
4. **Transports:** `stdio` (Claude Code spawn) or `sse` (HTTP, Starlette + StreamableHTTPSessionManager). The `AuthMiddleware` protects only the HTTP transport when `AUTH_ENABLED=true`. `POST /mcp` is rewritten in-process to `/mcp/` (no 307) so Streamable HTTP clients keep the configured `Authorization` header.

**Rule:** no tool imports repositories or SQL directly. Any new tool goes through the same use-case pipeline and inherits auth/rate-limiting/validation/logging for free.

---

## Persistence — `db/`

A **lightweight** repository layer (the article's "simplified architecture" — database models as plain objects, without heavy DDD):

| File | Aggregate |
|---|---|
| `connection.py` | Async psycopg pool + `run_migrations()` |
| `db/repository.py` | Artifacts (CRUD, pgvector semantic search, relationships, `flow` filter) |
| `db/project_repository.py` | Projects (multi-tenant registry; `default_flow`) |
| `db/rule_repository.py` | Harness rules (free-text `trigger`; `flow` filter) |
| `db/session_repository.py` | Working context per project |
| `db/skill_repository.py` | Global and project-specific skills (carry `flow`) |
| `db/trace_repository.py` | Episodic memory (executions + embeddings) |
| `db/api_key_repository.py` | API keys |
| `db/migrations/` | Versioned SQL (schema + pgvector HNSW indexes); `008_multi_flow.sql` adds the flow registry and free-text kinds |

Repositories return the pydantic models from `models/` — never raw rows. Functions are **module-level, async, and stateless** (the pool is shared via `connection.get_conn()`), so they follow the "pure functions" pattern of the frontend's services layer.

### Flow registry (multi-flow)

The core is **domain-agnostic**: SDD is the first **flow** (`flow='sdd'`), not the only one.
A flow is a pack of data — `kinds`, `harness_triggers`, `skills`, `commands` and
a `CLAUDE.md` section — with no server-specific code:

| File | Responsibility |
|---|---|
| `core/domain/flow_manifest.py` | Pure manifest schema (`FlowManifest`, `manifest_issues`, `validate_manifest`); optional `lifecycle` field (ordered phases `{name, kinds}` — validates unique names and references to declared kinds; web-ui-design-alignment REQ-006) |
| `db/flow_registry.py` | `ensure_sdd_flow`, `register_flow` (idempotent upsert into `flows`/`artifact_kinds`) |
| `core/domain/artifact_validation.py` | `validate_registered`: `(flow, kind)` precedence (built-in SDD → declarative → fallback) |
| `db/repository.get_artifact_kind_rules` | Reads `artifact_kinds.rules` for the `(flow, kind)` pair |

`artifacts.type` is **free text** (not an enum) and `artifacts`/`skills`/`project_rules`
carry `flow`; `projects.default_flow` resolves an omitted `flow`. The MCP tools
`create_artifact`/`list_artifacts`/`search_semantic`/`get_harness_checklist` accept
an optional `flow`, and `register_flow` ingests a manifest. On the client, each flow lives
in `client/src/templates/flows/<slug>/` and is installed via `init --flow`.

**UI multi-flow (web-ui-design-alignment):** the optional manifest `lifecycle`
(ordered phases `{name, kinds}`) feeds the **progress-based** phase derivation in
`core/domain/change_progress.py` — the pure, stdlib-only module whose functions
(`group_live_changes`, `derive_phases`, `task_progress`, `project_summary`) do all
live-change grouping and phase/progress computation; the management API only maps
its output. `GET /api/v1/projects` returns each project enriched with additive
fields — `change` (most recently updated live change, nullable), `phase` (project
phase, nullable), `phases` (mini pipeline `{name, status: done|active|pending}`)
and `task_progress` (`{done, total}`), computed over **live changes only** — and
`GET /api/v1/flows` exposes the registry. When no lifecycle is declared, `phase`
comes back `null` and the UI omits the phase strip (graceful degradation). The
`projects.language` column (migration 009) feeds the cards.

**Hierarchy (web-artifact-hierarchy):** `GET /api/v1/projects/:slug/tree` resolves
the active change (most recent non-archived `metadata.change_name`), the change's
artifacts and the `artifact_relationships` edges in a single join — returns
`{change, flows: [{flow, nodes (id/name/type/status/depth), edges}]}`. Canonical
depth: proposal 0, spec/design 1, task 2, test 3. The dashboard's Hierarchy tab
renders the tree as a vertical timeline (the prototype's pattern) with chips per
type and clickable nodes.

**Live changes (web-overview-changes-pipeline):**
`GET /api/v1/projects/:slug/changes` lists every live change of the project with
`started_at` (min artifact `created_at`), `updated_at`, `task_progress` and its
own progress-based phase pipeline (from the manifest lifecycle).
**API keys:** `GET/POST /api/v1/keys` and `POST /api/v1/keys/:id/revoke` manage
MCP Bearer keys (same `api_keys` table as the CLI). List/revoke payloads omit
`key` and `key_hash`; create returns plaintext once. This is the management
API (token `MANAGEMENT_API_TOKEN`), not the MCP `/mcp` authenticator — key
lookup and `AuthMiddleware` are unchanged.

`GET /api/v1/projects/:slug/changes/:change` is a separate resource: the
dashboard Change Reader's full-document bundle (`{change, flow, proposal,
design, specs, tasks, task_count}`). Members are every artifact whose
`metadata.change_name` matches (live or archived) — the same membership as MCP
`read_change_bundle`, but tasks include `content` and `done`. The MCP tool is
unchanged. Unknown slug or change returns HTTP 404. The list endpoint is
untouched and still has no artifact `content`. A **live
change** is any change whose artifacts include something other than an archived
artifact or a *synced main spec*; a synced main spec is one with
`metadata.is_delta != true` AND `status == active` (active non-delta specs of
changes still in flight still count as live). Phases are **progress-based**:
they are evaluated in lifecycle order and reached by evidence — a new artifact
kind appearing marks its phase reached, and a repeated-kind phase becomes
reachable once the previous phase's artifacts are all done; a phase counts as
done when all earlier phases are reached and done. Archived artifacts of the
change are included in the grouping (they are needed to mark early phases as
done). `task_progress` counts a task as done when `metadata.done == true` or its
status is `archived`. When a management request needs project-level aggregates,
`list_projects` enriches all projects in a constant number of queries by reading
artifact stubs via `list_artifact_stubs`. The dashboard's Overview renders a
paginated list of live changes (name, start date, stage); a row opens the
Change Reader.

---

## Embeddings — `embedding/`

An isolated component (wrapper around a 3rd-party library): `sentence-transformers` with the `all-MiniLM-L6-v2` model (384 dims). Consumed by the repositories when persisting/re-embedding artifacts and traces. Isolated in its own layer because it is the only coupling to an ML model — swapping the model is an internal change to the component, invisible to the rest.

---

## Where to put what

- New tool (MCP flow) → static definition in the registry + executor in `infrastructure/pg/tool_executors.py` (the registry and `EXECUTORS` are keyed by the same `tool.name`)
- New authoring/validation rule → `core/domain/` (e.g. an artifact/test validation rule)
- New external dependency in the core → define/extend a **Port** in `core/ports/` + an adapter in `infrastructure/` + wiring in `composition.py`
- New aggregate table → model in `models/` + repository in `db/` + migration in `db/migrations/`
- New **flow** (workflow) → pack on the client (`client/src/templates/flows/<slug>/` with `manifest.js` + `skills/` + `commands/`) registered via `register_flow`; **no** server code required
- New declarative validation rule per kind → `artifact_kinds.rules` (`required_headings` / `required_metadata_keys`), no Python code
- New administration command → sub-typer in `cli/<domain>.py` + wiring in `cli/main.py`
- New resource exposed via MCP resources → `infrastructure/mcp_resources.py`

---

## Communication Between Components (bad practice ↔ good practice, from the article)

| Mode | When to use | Example in the project |
|---|---|---|
| Direct call | Interface to the outside world (API/view) | `mcp/server.py` → `ExecuteToolUseCase` |
| Via port (abstract class) | Core component needs infrastructure | Use cases → `RateLimiterPort`, `LoggerPort` |
| **Avoided:** events (blinker) | No need to decouple events | — |

**Forbidden anti-dependencies:**
- Importing `db/repository` inside `mcp/` or `cli/` (tested)
- Importing adapters in `core/` (tested)
- `core/domain` importing anything with I/O (tested)
- DTOs: always via `Request`/`Response` — never expose a pydantic object from `models/` (a database entity) directly as a use case's return value.

---

## Tests

Focus per component, following the article:

1. **Component tests** exercise the public API (use cases against in-memory adapters) — the whole component is the unit. Avoid over-mocking at the edges.
2. **Architecture tests** (`tests/architecture/test_imports.py`) automate the import rules — the equivalent of the article's `pylint-forbidden-imports`, but as a simple pytest suite with no extra linter.
3. **Integration tests** cover real PostgreSQL communication (`db/` + pg adapters), making sure components talk to each other when running under `docker compose`.
4. **Stubs over mocks:** for the ports, we prefer simple hand-written stubs (minimal Protocol implementations) instead of framework-heavy mocks — see the article "[beware of chicken testing](https://breadcrumbscollector.tech/beware-of-chicken-testing-or-mocks-overuse/)".

---

## Checklist before finishing a backend change

- [ ] `core/` still imports only from `core/domain` and `core/ports`
- [ ] No database entity leaked through a use case (swap for a `Response`/DTO)
- [ ] New adapter implemented as a Protocol + registered in `composition.py`
- [ ] `pytest tests/architecture/ -q` passes
- [ ] No new circular imports (composition is the only "imports everything" module)
- [ ] New tool has: registry definition + executor + schema validated on input and output