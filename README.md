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

Verify they are running:

```bash
curl http://localhost:8000/health
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

## mcp-server (Python)

### Installation

```bash
cd mcp-server

# Install the package and dependencies
uv pip install -e .

# Run migrations and seed global SDD skills
opensddrag init
```

### Run locally (stdio mode)

Claude Code can spawn the server directly as a child process:

```bash
opensddrag server start
```

### Run as HTTP server (SSE mode)

For remote use or via Docker:

```bash
opensddrag server start --transport sse --port 8000
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
node bin/opensddrag.js init [--server http://localhost:8000] [--project <slug>] [--yes]
```

Options:
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

Claude Code spawns `opensddrag server start` as a child process. Communication happens over stdin/stdout. Ideal for local development where Claude Code and the server run on the same machine.

Configured via `.mcp.json` in the target project (generated by `client init`):

```json
{
  "mcpServers": {
    "opensddrag": {
      "type": "stdio",
      "command": "opensddrag",
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

## CLI Command Reference

All commands require the database to be reachable.

### Projects

```bash
opensddrag project list              # list all projects
opensddrag project create <slug>     # create a new project
opensddrag project show <slug>       # show project details
```

### Specs

```bash
opensddrag spec list                 # list specs for the active project
opensddrag spec create <name>        # create a spec
opensddrag spec show <id>            # show a specific spec
```

### Tasks

```bash
opensddrag task list                 # list tasks for the active project
opensddrag task create <description> # create a task
opensddrag task show <id>            # show a specific task
```

### Skills

```bash
opensddrag skill list                # list available skills
opensddrag skill create <name>       # create a skill
opensddrag skill suggest <query>     # suggest skills relevant to a query
```

### Semantic Search

```bash
opensddrag search semantic "<query>" # search artifacts by semantic similarity
```

### Session and Workspace

```bash
opensddrag session show              # show the active project's session context
opensddrag workspace init            # initialize the active project's workspace
```

### Import OpenSpec

Import planning artifacts from an OpenSpec project into OpenSddRag:

```bash
opensddrag import openspec /path/to/project              # import all changes and global specs
opensddrag import openspec /path/to/project --change add-auth   # import a single change only
opensddrag import openspec /path/to/project --force             # re-import and re-embed existing
opensddrag import openspec /path/to/project --project my-slug   # specify the target project
```

---

## License

See the `LICENSE` file at the repository root.
