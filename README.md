# OpenSddRag

**Spec-Driven Development (SDD) + Harness** — MCP server with persistent semantic memory and a structured workflow for disciplined software development.

---

## What is OpenSddRag

OpenSddRag gives AI agents (such as Claude Code) **persistent memory** and a **spec-driven workflow**. Instead of the agent working ad-hoc, every change flows through well-defined phases: propose → spec → design → tasks → apply → verify → archive.

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

| Table | Type | Description |
|---|---|---|
| `artifacts` | Semantic memory | Proposals, specs, designs, tasks — each with a `vector(384)` embedding |
| `execution_traces` | Episodic memory | Agent action log with embeddings for recall |
| `sessions` | Working context | Active artifact IDs + free-form JSON per project |
| `skills` | SDD templates | Global (`project_id IS NULL`) or project-scoped |
| `projects` | Multi-tenant registry | Projects registered in the system |
| `artifact_relationships` | Dependency graph | Links between artifacts (`depends_on`, `implements`, `relates_to`) |
| `project_rules` | Harness rules | Behavioral constraints enforced per SDD phase, with severity and trigger |

All vectors use HNSW indexes (`vector_cosine_ops`). Embeddings are 384 dimensions via `all-MiniLM-L6-v2`.

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
- **MCP server** (SSE mode) on port `8000`

Verify they are running (a `401` response is expected — auth is enabled by default):

```bash
curl http://localhost:8000/health
```

Then create an API key and connect your project:

```bash
# Create an API key (requires the Python venv)
cd mcp-server && source .venv/bin/activate
opensddrag-server key create --description "local dev"

# Connect a project (run from the target project root)
opensddrag init --api-key <key>
```

---

## Environment Configuration

Before running `mcp-server` locally (outside Docker), copy the example env file:

```bash
cp mcp-server/.env.example mcp-server/.env
```

Key variables in `mcp-server/.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://opensddrag:opensddrag@localhost:54326/opensddrag` | Database connection string |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model (sentence-transformers) |
| `OPENSDDRAG_PROJECT` | `default` | Active project slug |
| `AUTH_ENABLED` | `true` | Enables authentication in SSE mode |

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

Available endpoints in SSE mode:
- `GET /health` — health check
- `GET /sse` — SSE stream for the MCP client
- `POST /messages/` — MCP message endpoint
- `GET /api/projects` — list projects (used by the Node.js client)
- `POST /api/projects` — create a project (used by the Node.js client)

### Tests

```bash
cd mcp-server

pytest                          # all tests
pytest tests/test_foo.py        # specific file
pytest -k "test_name"           # test by name
```

---

## client (Node.js)

The client connects any software project to a running MCP server by installing the files Claude Code needs to communicate with OpenSddRag.

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
- `--api-key` — API key (required when `AUTH_ENABLED=true`)
- `--server` — MCP server URL (default: `http://localhost:8000`)
- `--project` — project slug to register (default: directory name)
- `--yes` — accept all prompts automatically

### What `init` installs in the target project

| File/Folder | Description |
|---|---|
| `.mcp.json` | Configures Claude Code to connect to the MCP server via SSE |
| `.claude/commands/opsr/*.md` | `/opsr:*` slash commands for Claude Code |
| `.claude/skills/opensddrag-*/SKILL.md` | OpenSddRag skills for Claude Code |
| `.agents/skills/opensddrag-*/SKILL.md` | Skills for other compatible agents |
| `CLAUDE.md` (section appended) | Instructs Claude Code about the OpenSddRag project |

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
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## SDD Flow

The complete spec-driven development workflow:

| Phase | Artifact | Description |
|---|---|---|
| **propose** | `proposal.md` | Defines what and why — problem, changes, affected capabilities |
| **spec** | `specs/<cap>/spec.md` | Defines what the system should do — testable requirements with WHEN/THEN scenarios |
| **design** | `design.md` | Defines how to implement — technical decisions, trade-offs, risks |
| **tasks** | `tasks.md` | Trackable task list with checkboxes |
| **apply** | (code) | Implement tasks, marking `[ ]` → `[x]` as you go |
| **verify** | (tests) | Validate that spec scenarios are satisfied |
| **sync deltas** | (delta specs) | Merge modified specs back to the base (`openspec/specs/`) |
| **archive** | (finalization) | Close the change, record in history |

### Slash Commands

Installed by `client init` into `.claude/commands/opsr/`:

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

## Harness

The Harness is a rules engine that enforces project-level behavioral constraints across SDD workflow phases. Rules survive context resets — they are stored in the database and injected into every agent session automatically.

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
