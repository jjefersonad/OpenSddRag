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

# Configure only OpenCode (skip Claude Code)
npx opensddrag init --tools opencode
```

**What gets created in your project**

| Path | Purpose |
|---|---|
| `.mcp.json` | Claude Code MCP server entry (`type: http`) |
| `opencode.json` | OpenCode MCP server entry (only with `--tools opencode`) |
| `.claude/skills/opensddrag-*/SKILL.md` | One skill file per SDD command |
| `.agents/skills/opensddrag-*/SKILL.md` | Same skills for agent-native tooling |
| `.opencode/skills/opensddrag-*/SKILL.md` | OpenCode-native skills (when selected) |
| `.claude/commands/opsr/*.md` | Claude Code slash commands |
| `.opencode/commands/opsr/*.md` | OpenCode slash commands (when selected) |
| `CLAUDE.md` | OpenSddRag section appended (or file created) |
| `opensddrag.yaml` | Local project marker (`project` + `server`) |

---

### `opensddrag status`

Check whether the current project is correctly wired to the server.

```bash
npx opensddrag status
```

Reports:
- `opensddrag.yaml` — local config found
- Skills — how many of the 13 expected skill files are present
- `.mcp.json` / `opencode.json` — MCP server entry
- Slash commands — which `/opsr:*` commands are installed
- `CLAUDE.md` — whether the OpenSddRag section exists
- Server — live health check + project registration confirmation

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
