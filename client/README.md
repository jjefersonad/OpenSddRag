# opensddrag

CLI client to connect any project to the [OpenSddRag](https://github.com/conexaoelite/OpenSddRag) SDD+Harness MCP server.

OpenSddRag implements **Spec-Driven Development (SDD)** — a structured workflow where every feature flows through `propose → spec → design → tasks → apply → archive`, backed by a PostgreSQL/pgvector semantic memory store. This CLI wires your project's AI tools to that server in seconds.

## Prerequisites

- Node.js ≥ 18
- A running OpenSddRag MCP server (see [server setup](#server-setup))

## Installation

```bash
# one-off, no install needed
npx opensddrag init

# or install globally
npm install -g opensddrag
opensddrag init
```

## Quick Start

```bash
# 1. Start the OpenSddRag server (Docker)
docker compose up -d          # runs on http://localhost:8000

# 2. Inside your project, connect it
cd my-project
npx opensddrag init

# 3. Open the project in Claude Code — the MCP server is ready
```

The `init` command registers your project on the server, writes MCP config files, installs SDD slash commands, and appends a section to `CLAUDE.md`.

## Commands

### `opensddrag init`

Connect the current directory to an OpenSddRag MCP server.

```
Options:
  --server <url>      Server URL  (default: http://localhost:8000)
  --project <slug>    Project slug  (default: directory name)
  --name <name>       Project display name
  --api-key <key>     API key for password-protected servers
  --tools <list>      AI tools to configure: claude, opencode  (default: ask)
  --yes               Skip all confirmation prompts
```

**Examples**

```bash
# Interactive — prompts for all values
npx opensddrag init

# Non-interactive — CI / scripted setup
npx opensddrag init --server http://localhost:8000 --project my-app --yes

# Remote server with an API key
npx opensddrag init --server https://sdd.example.com --api-key sk-... --yes

# CI — configure via env vars, no flags needed
OPENSDDRAG_SERVER_URL=http://mcp.internal:8000 OPENSDDRAG_API_KEY=sk-... npx opensddrag init --project my-app --yes

# Configure only OpenCode (skip Claude Code)
npx opensddrag init --tools opencode
```

**What gets created in your project**

| Path | Purpose |
|---|---|
| `.mcp.json` | Claude Code MCP server entry (`type: http`) |
| `opencode.json` | OpenCode MCP server entry (only with `--tools opencode`) |
| `.claude/skills/opensddrag-*/SKILL.md` | One skill file per SDD command |
| `.claude/skills/opensddrag-harness/SKILL.md` | Harness rule management skill |
| `.agents/skills/opensddrag-*/SKILL.md` | Same skills for agent-native tooling |
| `.agents/skills/opensddrag-harness/SKILL.md` | Same harness skill for agent-native tooling |
| `.opencode/skills/opensddrag-*/SKILL.md` | OpenCode-native skills (when selected) |
| `.opencode/skills/opensddrag-harness/SKILL.md` | OpenCode-native harness skill (when selected) |
| `.claude/commands/opsr/*.md` | Claude Code slash commands |
| `.opencode/commands/opsr/*.md` | OpenCode slash commands (when selected) |
| `CLAUDE.md` | OpenSddRag section appended (or file created) |
| `opensddrag.yaml` | Local project marker (`project` + `server`) |

---

### `opensddrag status`

Check whether the current project is correctly wired to the server.

```
Options:
  --server <url>   Override the server URL for this check
```

```bash
npx opensddrag status
npx opensddrag status --server http://mcp.internal:8000
```

Reports:
- `opensddrag.yaml` — local config found
- Skills — how many of the 13 expected skill files are present
- `.mcp.json` / `opencode.json` — MCP server entry
- Slash commands — which `/opsr:*` commands are installed
- `CLAUDE.md` — whether the OpenSddRag section exists
- Server — live health check + project registration confirmation

## Environment Variables

Both `init` and `status` support configuration via environment variables. Precedence order (first match wins):

1. `--server` / `--api-key` CLI flags
2. Environment variables
3. `opensddrag.yaml` (`server_url` or `server` field)
4. Built-in default (`http://localhost:8000`)

| Variable | Purpose |
|---|---|
| `OPENSDDRAG_SERVER_URL` | MCP server URL — used when no `--server` flag is passed |
| `OPENSDDRAG_API_KEY` | API key for authenticated servers — used when no `--api-key` flag is passed |

```bash
# Connect to a remote server without flags
export OPENSDDRAG_SERVER_URL=http://mcp.internal:8000
export OPENSDDRAG_API_KEY=sk-abc123
npx opensddrag init --project my-app --yes
npx opensddrag status
```

`OPENSDDRAG_API_KEY` is honored for any server URL — including `localhost` — so local servers with `AUTH_ENABLED=true` work correctly.

---

## SDD Slash Commands

After `init`, the following slash commands are available inside Claude Code (prefix `/opsr:`):

| Command | When to use |
|---|---|
| `/opsr:propose` | Capture intent and scope — start here |
| `/opsr:spec` | Formalize requirements (Purpose / SHALL / Scenarios) |
| `/opsr:design` | Document technical decisions and trade-offs |
| `/opsr:tasks` | Break a spec into atomic tasks (< 4 h each) |
| `/opsr:apply` | Implement the next pending task against spec criteria |
| `/opsr:verify` | Confirm a task is done and acceptance criteria are met |
| `/opsr:sync` | Merge delta specs after mid-flight design changes |
| `/opsr:archive` | Mark a completed feature as archived |
| `/opsr:explore` | Explore and investigate before committing to a plan |
| `/opsr:continue` | Resume the last in-progress artifact |
| `/opsr:status` | Show what is in progress and what is done |
| `/opsr:flow` | Run the full SDD flow end-to-end for a feature |
| `/opsr:search` | Semantic search over specs and past work |
| `/opsr:harness` | Add, list, or disable project rules enforced at SDD phase gates |

## Harness

The Harness is a rule-gate layer built on top of the SDD workflow. It lets you define persistent, per-project behavioral rules that are automatically injected into every agent session and enforced at specific SDD phase gates.

**How it works:**
- Rules are stored in the MCP server's database, scoped to your project.
- `always` rules are returned automatically by `get_working_context` at the start of every session.
- Phase-gate rules (`on_spec`, `on_apply`, `on_verify`, `on_archive`) are surfaced by `get_harness_checklist` when the corresponding SDD command runs its gate step.
- Agents check the checklist before completing each gate action and must satisfy all `error`-severity rules.

### Triggers

| Trigger | When it fires |
|---|---|
| `always` | Every agent session — injected via `get_working_context` |
| `on_spec` | Before saving a spec artifact (`/opsr:spec`) |
| `on_apply` | Before marking a task complete (`/opsr:apply`) |
| `on_verify` | Before declaring verification done (`/opsr:verify`) |
| `on_archive` | Before archiving change artifacts (`/opsr:archive`) |

### MCP Tools

| Tool | Description |
|---|---|
| `add_rule` | Create or update a project rule (name, trigger, category, severity, instruction) |
| `list_rules` | List all rules for the project, grouped by trigger |
| `get_harness_checklist` | Return enabled rules for a specific trigger — called by SDD commands at phase gates |

### Managing rules

```bash
# Inside Claude Code, after opensddrag init:

# Add a rule interactively
/opsr:harness add

# Add a rule directly
/opsr:harness add name=no-raw-sql trigger=on_apply category=forbidden severity=error instruction="Never write raw SQL strings — use the repository layer"

# List all rules
/opsr:harness list

# Disable a rule
/opsr:harness disable no-raw-sql
```

---

## Server Setup

The MCP server is a separate Python package (`opensddrag` on PyPI) that requires PostgreSQL with the pgvector extension.

**Docker (recommended)**

```bash
# Clone the repo or copy docker-compose.yml
git clone https://github.com/conexaoelite/OpenSddRag
cd OpenSddRag
docker compose up -d
```

The server starts on `http://localhost:8000`. The database runs on `localhost:54326`.

**Local (development)**

```bash
cd mcp-server
cp .env.example .env
uv pip install -e .
opensddrag init          # run migrations + seed global SDD skills
opensddrag server start --transport sse --port 8000
```

## License

MIT
