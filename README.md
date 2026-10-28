# OpenSddRag

**Spec-Driven Development (SDD) + Harness** — MCP server with persistent semantic memory and structured pipelines for disciplined software development. SDD is built in; you can register other flows.

---

## What is OpenSddRag

OpenSddRag gives AI agents (Claude Code, Cursor, OpenCode) **persistent memory** and a **pipeline** (flow) of versioned, embedded artifacts. SDD is the built-in pipeline (`propose → spec → design → tasks → apply → verify → archive`). Other pipelines declare their own phases and artifact kinds — see [Flows (pipelines)](#flows-pipelines).

### Two independent packages

| Package | Technology | Role |
|---|---|---|
| `mcp-server/` | Python + PostgreSQL/pgvector | Core MCP server: stores artifacts, traces, and session context |
| `client/` | Node.js | CLI that connects any project to a running MCP server |

### SDD concept (Spec-Driven Development)

All work follows an artifact lifecycle in dependency order:

```
proposal → spec(s) → design → tasks → apply → verify → sync deltas → archive
```

Each artifact lives in the database with a vector embedding, enabling semantic search over the project's decision history.

---

## Architecture

### Three memory layers

The core is **domain-agnostic** — SDD is the first **flow**, not the only one. Artifact kinds are free text and scoped by `flow`.

| Table | Type | Description |
|---|---|---|
| `artifacts` | Semantic memory | Proposals, specs, designs, tasks, tests and any flow's kinds — each with a `vector(384)` embedding; `type` is text, `flow` scopes the workflow (`'sdd'` by default) |
| `execution_traces` | Episodic memory | Agent action log with embeddings for recall |
| `sessions` | Working context | Active artifact IDs + free-form JSON per project |
| `skills` | Skill templates | Global (`project_id IS NULL`) or project-scoped; carry `flow` |
| `projects` | Multi-tenant registry | Projects registered in the system; `default_flow` resolves an omitted `flow` |
| `artifact_relationships` | Dependency graph | Links between artifacts (`depends_on`, `implements`, `relates_to`) — cross-flow links allowed |
| `project_rules` | Harness rules | Behavioral constraints per phase (`trigger` is free text); carry `flow` |
| `flows` | Flow registry | One row per workflow (`manifest` JSONB), seeded with `sdd` |
| `artifact_kinds` | Kind registry | `(flow, kind)` pairs with declarative `rules` (`required_headings`, `required_metadata_keys`) |

All vectors use HNSW indexes (`vector_cosine_ops`). Embeddings are 384 dimensions via `all-MiniLM-L6-v2`.

For the server-side layer model (Clean Architecture) see [mcp-server/docs/architecture/clean-architecture.md](mcp-server/docs/architecture/clean-architecture.md).

---

## Prerequisites

- **Docker** and **Docker Compose** (for running the database and MCP server in containers)
- **Python 3.11+** and **[uv](https://github.com/astral-sh/uv)** (to run `mcp-server` locally)
- **Node.js 18+** and **npm** (for the `client`)

---

## Quick Start

The simplest way to bring up the database and MCP server together:

```bash
docker compose up -d
```

This starts:
- **PostgreSQL/pgvector** on port `54326` (mapped from the container)
- **MCP server** (SSE mode) + management API on port `8000`
- **Dashboard** on [http://localhost:3001](http://localhost:3001) — login with `MANAGEMENT_API_TOKEN` (Compose default `123456`)

Verify they are running (a `401` response is expected — auth is enabled by default):

```bash
curl -i http://localhost:8000/mcp/
```

Then create an API key and connect your project:

```bash
# Create an MCP API key: dashboard → API keys, or the Python CLI:
cd mcp-server && source .venv/bin/activate
opensddrag-server key create --description "local dev"

# Connect a project (run from the target project root)
opensddrag init --api-key <key>
```

The dashboard token and the MCP API key are different secrets. Do not put `MANAGEMENT_API_TOKEN` in `.mcp.json`.

---

## Environment Configuration

Before running `mcp-server` locally (outside Docker), copy the example env file:

```bash
cp mcp-server/.env.example mcp-server/.env
```

Key variables in `mcp-server/.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://opensddrag:opensddrag@localhost:54326/opensddrag` | Database connection string (host port `54326` when talking to Compose from the host) |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model (sentence-transformers) |
| `OPENSDDRAG_PROJECT` | `default` | Active project slug |
| `AUTH_ENABLED` | `true` | Enables authentication in SSE mode |
| `MANAGEMENT_API_TOKEN` | `123456` (Compose) | Bearer token for `/api/v1` and the dashboard login — not an MCP API key |
| `WEB_ORIGIN` | `http://localhost:3001` | CORS origin for the dashboard |
| `SERVE_WEB_UI` | `false` | Serve the built dashboard from the MCP process itself |

---

## Authentication

The MCP server requires an API key in SSE mode when `AUTH_ENABLED=true` (the default). API keys are managed via the `opensddrag-server` CLI, which connects directly to the database — no running server required.

Activate the Python venv first:

```bash
cd mcp-server && source .venv/bin/activate
```

### Create an API key

```bash
# Global key — works with any project
opensddrag-server key create --description "local dev"

# Project-scoped key — restricted to a specific project
opensddrag-server key create --project <slug> --description "prod key"

# With expiry date
opensddrag-server key create --description "ci key" --expires-at 2027-01-01
```

The plaintext key is shown only once — save it immediately.

### Use the key

Pass it to `opensddrag init`:

```bash
opensddrag init --api-key <key>
```

### Manage keys

```bash
opensddrag-server key list                # list all keys with status
opensddrag-server key revoke <key-id>     # revoke a key by UUID
```

### Disable auth (local development only)

Set `AUTH_ENABLED=false` in `docker-compose.yml` or `mcp-server/.env` and restart:

```bash
docker compose up -d --force-recreate
```

---

## mcp-server (Python)

### Installation

```bash
cd mcp-server

# Install the package and dependencies
uv pip install -e .

# Run migrations and seed global SDD skills
opensddrag-server init
```

### Run locally (stdio mode)

Claude Code can spawn the server directly as a child process:

```bash
opensddrag-server server start
```

### Run as HTTP server (SSE mode)

For remote use or via Docker:

```bash
opensddrag-server server start --transport sse --port 8000
```

Available endpoints in HTTP/SSE mode:
- `POST /mcp` — MCP streamable-HTTP transport (auth: `Authorization: Bearer <api-key>`)
- `GET /api/v1/projects` — list projects (management API; auth: `Authorization: Bearer <MANAGEMENT_API_TOKEN>`). Each entry is enriched with additive fields — `change` (most recently updated live change, nullable), `phase` (project phase, nullable), `phases` (mini pipeline of `{name, status}`) and `task_progress` (`{done, total}` over live changes only) — all derived per request from `core/domain/change_progress.py`
- `POST /api/v1/projects` — create a project (management API; optional `language`)
- `GET /api/v1/projects/:slug/artifacts?type=...&flow=...` — list artifacts, optionally filtered by flow. Add `&include=content` to opt in to full artifact content; summaries ship **without** content by default, and any other `include` value is rejected with `422`
- `GET /api/v1/projects/:slug/session` — working-context summary (active artifacts + note)
- `GET /api/v1/search?q=...` — semantic search (management API)
- `GET /api/v1/flows` — registered flows with kinds + lifecycle (management API)
- `GET /api/v1/projects/:slug/tree` — active change artifact hierarchy (nodes + edges per flow)
- `GET /api/v1/projects/:slug/changes` — live changes in progress, each with `started_at` (earliest artifact `created_at`), `updated_at`, `task_progress` and a progress-based phase pipeline (see the data definitions below). List payload has **no** artifact `content`.
- `GET /api/v1/projects/:slug/changes/:change` — one change's document bundle for the dashboard reader (auth: `Authorization: Bearer <MANAGEMENT_API_TOKEN>`). Response shape: `{change, flow, proposal, design, specs, tasks, task_count}` where `proposal`/`design` are full artifacts or `null`, `specs` are full artifacts (including `content`), and `tasks` are `{name, status, content, done}` (`done` is true when status is `archived` or `metadata.done`). Membership is `metadata.change_name` (same as MCP `read_change_bundle`); this REST path is **not** the MCP tool — MCP still omits task bodies. Unknown slug or change → HTTP 404.
- `GET /api/v1/keys` — list MCP API keys (`?project=<slug>`, `?scope=global`, `?include_revoked=true`). Never returns plaintext or hash. Default listing omits revoked keys.
- `POST /api/v1/keys` — create a key (`description`, optional `project_slug`, optional `expires_at`). Response includes `key` once.
- `POST /api/v1/keys/:id/revoke` — revoke a key (connected MCP clients then get 401). The dashboard **API keys** page (`/keys`) uses these endpoints.
- `GET /` — built web dashboard, served only when `SERVE_WEB_UI=true`. The dashboard loads **IBM Plex Sans/Mono** via Google Fonts (a `<link>` in `web/index.html`; the token fallback stack lives in `web/src/styles/tokens.css`). Its visual fidelity is verified with `scripts/ui-fidelity/check.py` (a Playwright for Python script — a documented prerequisite, not a package.json dependency) against `docs/ui/FIDELITY_CHECKLIST.md` (the human-readable criteria list)

Flow manifests may declare an optional `lifecycle` (ordered phases mapping artifact kinds), so the dashboard derives per-flow progress from data — new flows render without UI changes.

**Dashboard data definitions.** A **live change** is any change whose artifacts include something other than an archived artifact or a *synced main spec*; a synced main spec is a spec with `metadata.is_delta != true` AND `status == active` (active non-delta specs of changes still in flight still count as live). A **task is done** when `metadata.done == true` or its status is `archived`. Per-change **phases are progress-based**: phases are evaluated in lifecycle order and reached by evidence (a new artifact kind appearing marks the phase reached; repeated-kind phases become reachable once the previous phase's artifacts are done), and a phase counts as done when all earlier phases are reached and done. Project-level aggregates (`change`, `phase`, `task_progress`) are computed over **live changes only**.

### Tests

```bash
cd mcp-server

pytest                          # all tests
pytest tests/test_foo.py        # specific file
pytest -k "test_name"           # test by name
```

---

## client (Node.js)

The client connects any software project to a running MCP server by installing the files Claude Code, Cursor, and OpenCode need to talk to OpenSddRag.

### Installation

```bash
cd client
npm install
```

### Connect a project to the MCP server

Run from the **root of the target project** (not this repository):

```bash
# When AUTH_ENABLED=true (default), pass your API key:
opensddrag init --api-key <key> [--server http://localhost:8000] [--project <slug>] [--yes]
```

Options:
- `--api-key` — MCP API key (required when `AUTH_ENABLED=true`)
- `--server` — MCP server URL (default: `http://localhost:8000`)
- `--project` — project slug to register (default: directory name)
- `--tools claude,opencode` — which AI tools to write config for (default: ask)
- `--flow sdd,docs` — pipelines to install (default with `--yes`: `sdd` only)
- `--yes` — accept all prompts automatically

### What `init` installs in the target project

`opensddrag init` installs the selected flow(s) — default `sdd`, or `--flow sdd,docs`:

| File/Folder | Description |
|---|---|
| `.mcp.json` | Configures Claude Code (and Cursor) to connect to the MCP server via HTTP |
| `.claude/commands/opsr/*.md` | `/opsr:*` slash commands for Claude Code (non-SDD flows nest under `opsr/<flow>/`) |
| `.claude/skills/opensddrag-*/SKILL.md` | OpenSddRag skills for Claude Code (non-SDD flows prefix `opensddrag-<flow>-`) |
| `.agents/skills/opensddrag-*/SKILL.md` | Skills for other compatible agents |
| `CLAUDE.md` (section appended) | Instructs Claude Code about the OpenSddRag project (one section per flow) |

### Check connection status

```bash
node bin/opensddrag.js status
```

---

## MCP Transports

### stdio (local use)

Claude Code spawns `opensddrag-server server start` as a child process. Communication happens over stdin/stdout. Ideal for local development where Claude Code and the server run on the same machine.

Configured via `.mcp.json` in the target project (generated by `client init`):

```json
{
  "mcpServers": {
    "opensddrag": {
      "type": "stdio",
      "command": "opensddrag-server",
      "args": ["server", "start"]
    }
  }
}
```

### SSE (remote or Docker)

The server exposes HTTP endpoints. Suitable when the MCP server runs in Docker, on another machine, or is shared across multiple developers.

Configured via `.mcp.json` pointing to the SSE endpoint:

```json
{
  "mcpServers": {
    "opensddrag": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer <mcp-api-key>"
      }
    }
  }
}
```

Claude Code and Cursor both read this file. Do not put `MANAGEMENT_API_TOKEN` in the Bearer header.

---

## SDD Flow (built-in pipeline)

SDD is the built-in `flow=sdd`. Artifacts live in the database (with embeddings) — the MCP server does not write local markdown files. Heading contracts and how to register other pipelines are in [Flows (pipelines)](#flows-pipelines).

| Phase | Artifact kind | Description |
|---|---|---|
| **propose** | `proposal` | Defines what and why — problem, changes, affected capabilities |
| **spec** | `spec` (+ scenario `test`) | Testable SHALL/MUST requirements with WHEN/THEN scenarios |
| **design** | `design` | How to implement — technical decisions, rejected alternatives, risks |
| **tasks** | `task` (+ unit `test`) | Atomic, verifiable units |
| **apply** | (code + unit tests) | RED → GREEN → REFACTOR per unit; update `test_status` |
| **verify** | (scenario `test` status) | Confirm spec scenarios from linked unit tests |
| **sync** | (delta specs → main specs) | Merge modified capability specs |
| **archive** | (change artifacts archived) | Close the change, record in history |

### Slash Commands

Installed by `opensddrag init` into `.claude/commands/opsr/` (and `.opencode/commands/opsr/` when OpenCode is selected):

| Command | Phase | Description |
|---|---|---|
| `/opsr:propose` | Propose | Creates the proposal and guides through change definition |
| `/opsr:spec` | Spec | Generates capability specs based on the proposal |
| `/opsr:design` | Design | Creates the technical design document |
| `/opsr:tasks` | Planning | Breaks the design into implementable tasks |
| `/opsr:apply` | Implementation | Implements tasks sequentially, tracking progress |
| `/opsr:verify` | Verification | Validates spec scenarios against implemented code |
| `/opsr:sync` | Sync | Merges delta specs back into base specs |
| `/opsr:archive` | Archive | Finalizes and archives the change |
| `/opsr:explore` | Explore | Investigates problems before proposing a change |
| `/opsr:continue` | Continue | Resumes an in-progress change |
| `/opsr:status` | Status | Shows current state of all active changes |
| `/opsr:flow` | Flow | Interactive guide through the next SDD step |
| `/opsr:search` | Search | Semantic search over artifacts and traces |

---

## Flows (pipelines)

OpenSddRag is not SDD-only. A **flow** is a named pipeline pack — `kinds`,
optional `lifecycle` phases, harness triggers, skills, slash commands and a
`CLAUDE.md` section — stored as data (no per-flow server code). The dashboard
derives progress from `lifecycle`, so a new pipeline renders without UI
changes.

- **`sdd`** is the built-in flow (bare `/opsr:*`, `opensddrag-*` skills).
- **Register a flow**: `opensddrag-server register-flow <manifest.json>` (CLI)
  or the `register_flow` MCP tool (used by `opensddrag init`).
- **Install flows into a project**: `opensddrag init --flow sdd,docs` — non-SDD
  flows get namespaced commands (`/opsr:<flow>:<command>`), prefixed skills
  (`opensddrag-<flow>-<command>`) and their own `CLAUDE.md` section. Omitting
  `--flow` with `--yes` installs `sdd` alone (unchanged behaviour).
- **Validation by `(flow, kind)`**: built-in SDD validators for `spec`/`task`,
  otherwise declarative rules from `artifact_kinds` (`required_headings` /
  `required_metadata_keys`), otherwise a structural fallback.
- **Resolution**: MCP tools accept an optional `flow`, resolved from the
  project's `default_flow` and finally `'sdd'`.
- **Formats belong to the flow**: SDD's proposal/spec/design/task/test
  headings are the `sdd` kinds, not a global schema. A custom pipeline
  declares its own kinds and `required_headings` in the manifest.

### Built-in pipeline: SDD

Lifecycle (commands stay bare `/opsr:*`):

```
propose → spec → design → tasks → apply → verify → sync → archive
```

| Kind | Headings / contract |
|---|---|
| `proposal` | `## Why`, `## What Changes`, `## Capabilities`, `## Impact` |
| `spec` | `## Purpose`, `## Requirements`, `#### Scenario:` WHEN/THEN; deltas use `metadata.is_delta` |
| `design` | `## Decisions` (chosen + rejected), `## Risks / Trade-offs` |
| `task` | `## Goal`, `## Acceptance Criteria`, `## Dependencies`; `test_exempt` + `## Reason` when there is no unit |
| `test` | `metadata.level` = `scenario` \| `unit`; `test_status` = pending → failing → passing |

Utility commands (`explore`, `continue`, `status`, `flow`, `search`, `harness`) are not lifecycle phases.

### Create a custom pipeline

Write a kebab-case manifest (JSON, snake_case) and register it. `lifecycle`
is optional; when present, each phase maps a display name to declared kinds
(closing phases may use an empty `kinds` list):

```json
{
  "flow": "docs",
  "kinds": [
    { "kind": "brief" },
    { "kind": "draft", "required_headings": ["## Audience"] },
    { "kind": "publish" }
  ],
  "lifecycle": [
    { "name": "Brief", "kinds": ["brief"] },
    { "name": "Draft", "kinds": ["draft"] },
    { "name": "Publish", "kinds": ["publish"] }
  ],
  "harness_triggers": ["on_draft", "on_publish"],
  "skills": ["opensddrag-docs-draft", "opensddrag-docs-publish"],
  "commands": [{ "name": "draft" }, { "name": "publish" }],
  "claude_md_section": "## OpenSddRag — docs pipeline\n"
}
```

```bash
opensddrag-server register-flow ./docs-manifest.json
```

After registration, `create_artifact` / `validate_artifact` accept the new
kinds. To also install slash commands and skills into a target project, add
a pack at `client/src/templates/flows/<slug>/` (`manifest.js` + `skills/` +
`commands/`) and run `opensddrag init --flow <slug>`. The npm CLI README
([opensddrag](https://www.npmjs.com/package/opensddrag)) documents the same
flow for package consumers.

---

## Harness

The Harness is a per-project rules engine. Rules survive context resets — they are stored in the database and injected into every agent session automatically. SDD uses `on_spec` / `on_apply` / `on_verify` / `on_archive`; `add_rule` currently accepts those plus `always` even when a custom pipeline lists other trigger names.

### How it works

- Rules are stored per project with a **trigger**, **category**, **severity**, and a plain-English **instruction**
- Rules with `trigger="always"` are automatically injected into the `rules` key of `get_working_context` — every agent session starts with them loaded, with no extra tool call
- Phase-specific rules are surfaced as a checklist via `get_harness_checklist` inside `/opsr:apply`, `/opsr:verify`, `/opsr:spec`, and `/opsr:archive` before each gate executes

### Rule fields

| Field | Values | Description |
|---|---|---|
| `trigger` | `always`, `on_apply`, `on_verify`, `on_archive`, `on_spec` | When the rule fires |
| `category` | `architecture`, `naming`, `forbidden`, `doc-sync`, `verification` | Rule family |
| `severity` | `error`, `warning`, `info` | How the agent should weigh a violation |
| `instruction` | (free text) | Human-readable guidance the agent must follow |
| `enabled` | `true` / `false` | `false` soft-deletes the rule |

### MCP tools

| Tool | Description |
|---|---|
| `add_rule` | Create or upsert a rule (idempotent on `(project_slug, name)`) |
| `list_rules` | List active rules; pass `enabled_only=false` to include disabled rules |
| `get_harness_checklist` | Return enabled rules for a phase trigger, ordered by severity then name |

### `/opsr:harness` command

`opensddrag init` installs an `/opsr:harness` slash command and an `opensddrag-harness` skill into the connected project. Use it to manage rules directly from Claude Code:

```
/opsr:harness
```

The command guides the agent through adding, listing, and disabling project rules via the MCP tools above.

### Examples

**Structural invariant (injected into every session):**

```
add_rule
  name: "no-direct-db-in-controllers"
  trigger: "always"
  category: "architecture"
  severity: "error"
  instruction: "Controllers must never import database modules directly. All DB access must go through a repository or service layer."
```

**Phase gate (checked before every apply):**

```
add_rule
  name: "migrations-separate-task"
  trigger: "on_apply"
  category: "architecture"
  severity: "warning"
  instruction: "Database migrations must be implemented in a dedicated task, separate from application code changes."
```

**Disable a rule:**

```
add_rule
  name: "migrations-separate-task"
  enabled: false
```

---

## CLI Command Reference

All commands require the database to be reachable.

### Projects

```bash
opensddrag-server project list              # list all projects
opensddrag-server project create <slug>     # create a new project
opensddrag-server project show <slug>       # show project details
```

### Specs

```bash
opensddrag-server spec list                 # list specs for the active project
opensddrag-server spec create <name>        # create a spec
opensddrag-server spec show <id>            # show a specific spec
```

### Tasks

```bash
opensddrag-server task list                 # list tasks for the active project
opensddrag-server task create <description> # create a task
opensddrag-server task show <id>            # show a specific task
```

### Skills

```bash
opensddrag-server skill list                # list available skills
opensddrag-server skill create <name>       # create a skill
opensddrag-server skill suggest <query>     # suggest skills relevant to a query
```

### Semantic Search

```bash
opensddrag-server search semantic "<query>" # search artifacts by semantic similarity
```

### Session and Workspace

```bash
opensddrag-server session show              # show the active project's session context
opensddrag-server workspace init            # initialize the active project's workspace
```

### Import OpenSpec

Import planning artifacts from an OpenSpec project into OpenSddRag:

```bash
opensddrag-server import openspec /path/to/project              # import all changes and global specs
opensddrag-server import openspec /path/to/project --change add-auth   # import a single change only
opensddrag-server import openspec /path/to/project --force             # re-import and re-embed existing
opensddrag-server import openspec /path/to/project --project my-slug   # specify the target project
```

### API Keys

Manage API keys for SSE-mode authentication. Requires the Python venv to be active (`cd mcp-server && source .venv/bin/activate`).

```bash
opensddrag-server key create                               # create a global key
opensddrag-server key create --project <slug>              # project-scoped key
opensddrag-server key create --description "label"         # with description
opensddrag-server key create --expires-at 2027-01-01       # with expiry
opensddrag-server key list                                 # list all keys with status
opensddrag-server key revoke <key-id>                      # revoke a key by UUID
```

---

## License

See the `LICENSE` file at the repository root.
