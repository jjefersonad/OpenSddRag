# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

OpenSddRag is a **Spec-Driven Development (SDD) + Harness system** delivered as an MCP server backed by PostgreSQL/pgvector. It provides AI agents with persistent semantic memory (artifacts, execution traces, working context) and a structured workflow (propose → spec → design → tasks → apply → archive) for disciplined software development.

The repo has two independent packages:
- **`mcp-server/`** — Python MCP server (the core system)
- **`client/`** — Node.js CLI that connects any project to a running MCP server

## Infrastructure

Start the database and MCP server (SSE mode, port 8000):
```bash
docker compose up -d
```

Database runs on `localhost:54326` (pgvector/pg16). Copy `mcp-server/.env.example` to `mcp-server/.env` before running locally.

## mcp-server (Python)

**Setup** (from `mcp-server/`):
```bash
uv pip install -e .                # install with dependencies
opensddrag-server init             # run migrations + seed global SDD skills
```

**Run locally** (stdio transport — Claude Code spawns the process directly):
```bash
opensddrag-server server start
```

**Run as HTTP server** (SSE transport):
```bash
opensddrag-server server start --transport sse --port 8000
```

**Tests** (from `mcp-server/`):
```bash
pytest                       # run all tests
pytest tests/test_foo.py     # run a single file
pytest -k "test_name"        # run a single test
```

**CLI commands** (all require the database to be reachable):
```bash
opensddrag-server project list/create/show
opensddrag-server spec list/create/show
opensddrag-server task list/create/show
opensddrag-server skill list/create/suggest
opensddrag-server search semantic <query>
opensddrag-server session show
opensddrag-server workspace init

# Import OpenSpec planning artifacts into OpenSddRag
opensddrag-server import openspec /path/to/project              # import all changes + global specs
opensddrag-server import openspec /path/to/project --change add-auth  # single change only
opensddrag-server import openspec /path/to/project --force      # re-import and re-embed existing
opensddrag-server import openspec /path/to/project --project myslug   # specify target project
```

Config is loaded from environment variables or `.env` via `pydantic-settings` (`src/opensddrag/config.py`). Key variables: `DATABASE_URL`, `EMBEDDING_MODEL`, `OPENSDDRAG_PROJECT`.

## client (Node.js)

**Setup** (from `client/`):
```bash
npm install
```

**Connect a project to a running MCP server** (run from the target project's root):
```bash
node bin/opensddrag.js init [--server http://localhost:8000] [--project <slug>] [--yes]
node bin/opensddrag.js status
```

`init` writes to the target project (not this repo): `.mcp.json` (Claude Code MCP config), `.claude/commands/opsr/*.md` (slash commands), `.claude/skills/opensddrag-*/SKILL.md` and `.agents/skills/opensddrag-*/SKILL.md` (skill files), and appends an OpenSddRag section to `CLAUDE.md`.

## Architecture

### mcp-server layers

```
src/opensddrag/
  config.py               — pydantic-settings, reads .env
  mcp/server.py           — MCP tool + resource definitions and dispatch
  cli/main.py             — typer CLI root, wires sub-typers
  cli/_seeds.py           — seeds global SDD skills on init
  cli/server.py           — `opensddrag-server server start` (stdio or SSE)
  db/connection.py        — async psycopg connection pool + run_migrations()
  db/migrations/001_initial.sql — schema (pgvector HNSW indexes)
  db/repository.py        — artifact CRUD + semantic search + relationships
  db/project_repository.py
  db/session_repository.py
  db/skill_repository.py
  db/trace_repository.py
  embedding/service.py    — sentence-transformers embed()
  models/                 — pydantic models for all DB entities
```

### Database schema (3 memory types)

| Table | Purpose |
|---|---|
| `artifacts` | **Semantic memory** — proposals, specs, designs, tasks, changes; each has a `vector(384)` embedding |
| `artifact_relationships` | Links between artifacts (`depends_on`, `implements`, `relates_to`) |
| `execution_traces` | **Episodic memory** — agent action log with embeddings for recall |
| `sessions` | **Working context** — active artifact IDs + free-form JSON context per project |
| `skills` | SDD skill templates (global when `project_id IS NULL`, project-specific otherwise) |
| `projects` | Multi-tenant project registry |

All vector columns use HNSW indexes (`vector_cosine_ops`). Embeddings are 384-dimension (`all-MiniLM-L6-v2`).

### MCP transports

- **stdio**: Claude Code spawns `opensddrag-server server start` as a child process. Configured via `.mcp.json` in the client project with `type: "http"` pointing to the SSE endpoint.
- **SSE**: Starlette app (`/sse` + `/messages/`) for Docker/remote use. Also exposes a small REST API (`/health`, `GET /api/projects`, `POST /api/projects`) used by the Node.js client.

### SDD artifact lifecycle

Every piece of work flows through artifact types in dependency order:
```
proposal → spec(s) → design → task(s) → [apply] → [verify] → [sync deltas] → archive
```

- Artifact names follow a convention: `<change-name>-proposal`, `<change-name>-<capability>-spec`, `<change-name>-design`, `<change-name>-task-<group>-<N>`
- Delta specs (for modified capabilities) carry `metadata.is_delta = true` and are merged into main specs by `/opsr:sync`
- All artifacts live in the database — no local markdown files are created by the MCP server

### Slash commands (installed into client projects by `opensddrag init`)

Commands are installed to `.claude/commands/opsr/` and invoked as `/opsr:<name>` inside Claude Code. Each command file is a structured prompt that drives the AI through a specific SDD phase using the MCP tools. The templates live in `client/src/templates/commands/index.js`.

Available commands: `propose`, `spec`, `design`, `tasks`, `apply`, `verify`, `sync`, `archive`, `explore`, `continue`, `status`, `flow`, `search`.

## Language Convention

All project-level text **must be written in English**: source code, inline comments, SQL migration comments, documentation files (`README.md`, `docs/`, `CLAUDE.md`), CLI help strings, and planning artifacts inside `openspec/`.

Database-persisted content — artifacts (proposals, specs, designs, tasks), execution traces, skills, and session context — is **language-agnostic**. Store it exactly as the user writes it. Never translate, reject, or modify content based on detected language.
