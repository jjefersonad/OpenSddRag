# opensddrag

CLI client to connect any project to the [OpenSddRag](https://github.com/conexaoelite/OpenSddRag) SDD+Harness MCP server.

OpenSddRag implements **Spec-Driven Development (SDD)** plus extra **pipelines** (called *flows*). SDD is the built-in pipeline:

```
propose → spec → design → tasks → apply → verify → sync → archive
```

Each pipeline is a named pack of artifact kinds, optional lifecycle phases (shown on the dashboard), harness triggers, skills, and slash commands. You can install extra pipelines alongside SDD, or register your own — no server code change. This CLI wires your project's AI tools to that server in seconds. See [Flows (pipelines)](#flows-pipelines).

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
# 1. Start the stack (DB :54326, MCP :8000, dashboard :3001)
docker compose up -d

# 2. Create an MCP API key (dashboard /keys, or opensddrag-server key create)
#    Dashboard login is MANAGEMENT_API_TOKEN (Compose default: 123456) — not the MCP key.

# 3. Inside your project, connect it
cd my-project
npx opensddrag init --server http://localhost:8000 --api-key <key> --tools claude,opencode --yes

# 4. Reload Claude Code, OpenCode, or Cursor — the MCP server is ready
```

The `init` command registers your project on the server, writes MCP config files, installs slash commands for the selected pipeline(s) (SDD by default), and appends a section to `CLAUDE.md`.

## Commands

### `opensddrag init`

Connect the current directory to an OpenSddRag MCP server.

```
Options:
  --server <url>      Server URL  (default: http://localhost:8000)
  --project <slug>    Project slug  (default: directory name)
  --name <name>       Project display name
  --api-key <key>     API key for password-protected servers
  --tools <list>      AI tools to configure: claude, opencode  (default: ask). Cursor reads the same `.mcp.json` as Claude Code.
  --flow <slugs>      Pipelines to install, comma-separated  (default: sdd)
  --yes               Skip all confirmation prompts
```

Without `--flow`, `--yes` installs **SDD only**. Interactive init lets you pick every pipeline the CLI ships.

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

# SDD plus another shipped pipeline
npx opensddrag init --flow sdd,docs --yes
```

**What gets created in your project**

| Path | Purpose |
|---|---|
| `.mcp.json` | Claude Code and Cursor MCP server entry (`type: http`) |
| `opencode.json` | OpenCode MCP server entry (only with `--tools opencode`) |
| `.claude/skills/opensddrag-*/SKILL.md` | One skill file per command (`opensddrag-<flow>-*` for non-SDD pipelines) |
| `.claude/skills/opensddrag-harness/SKILL.md` | Harness rule management skill |
| `.agents/skills/opensddrag-*/SKILL.md` | Same skills for agent-native tooling |
| `.agents/skills/opensddrag-harness/SKILL.md` | Same harness skill for agent-native tooling |
| `.opencode/skills/opensddrag-*/SKILL.md` | OpenCode-native skills (when selected) |
| `.opencode/skills/opensddrag-harness/SKILL.md` | OpenCode-native harness skill (when selected) |
| `.claude/commands/opsr/*.md` | Claude Code slash commands (SDD: `/opsr:<command>`; other pipelines: `/opsr:<flow>:<command>` under `opsr/<flow>/`) |
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

## Flows (pipelines)

A **flow** is a named pipeline: artifact kinds, optional `lifecycle` phases (the dashboard derives progress from these — new pipelines render without UI changes), harness triggers, skills, and slash commands.

| | SDD (built-in) | Any other pipeline |
|---|---|---|
| Install | `opensddrag init` (default) | `opensddrag init --flow sdd,<slug>` |
| Slash commands | `/opsr:propose`, `/opsr:spec`, … | `/opsr:<slug>:<command>` |
| Skills | `opensddrag-<command>` | `opensddrag-<slug>-<command>` |
| Server registration | Seeded by the MCP server | `init` calls `register_flow`; or register a manifest yourself |

MCP tools take an optional `flow` argument (defaults to the project's `default_flow`, else `sdd`). Artifacts from different pipelines can still link to each other. Validation is by `(flow, kind)`: built-in SDD rules for `spec`/`task`, otherwise the kind's `required_headings` / `required_metadata_keys`, otherwise a structural fallback.

Workflow and artifact formats are **per pipeline**. SDD's propose→spec→design… sequence and its heading contracts apply only to `flow=sdd`. A custom pipeline replaces both with its own `lifecycle` and kind rules (the dashboard **Pipelines** page documents the same model).

### Built-in SDD (formats)

| Kind | Headings / contract |
|---|---|
| `proposal` | `## Why`, `## What Changes`, `## Capabilities`, `## Impact` |
| `spec` | `## Purpose`, `## Requirements`, `#### Scenario:` WHEN/THEN |
| `design` | `## Decisions`, `## Risks / Trade-offs` |
| `task` | `## Goal`, `## Acceptance Criteria`, `## Dependencies` |
| `test` | `level` = scenario \| unit; `test_status` = pending → failing → passing |

### Create a custom pipeline

Two pieces: a **manifest** the server understands, and (optionally) skills/commands the CLI installs into the target project.

**1. Register the pipeline with the MCP server** — JSON, snake_case. The slug must be kebab-case. `lifecycle` is optional; when present, the dashboard shows those phases instead of hard-coding SDD.

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
  "commands": [
    { "name": "draft" },
    { "name": "publish" }
  ],
  "claude_md_section": "## OpenSddRag — docs pipeline\n\n`/opsr:docs:draft` → `/opsr:docs:publish`\n"
}
```

Register it with the MCP tool `register_flow` (from an agent session) or the server CLI:

```bash
opensddrag-server register-flow ./docs-manifest.json
```

After that, `create_artifact` / `validate_artifact` accept the new kinds, and the dashboard renders the declared phases. No server code change is required.

**2. Ship skills and commands with the CLI** (only if you maintain this package or a fork). Add a pack at `src/templates/flows/<slug>/`:

```
src/templates/flows/<slug>/
  manifest.js      # { flow, kinds, lifecycle, harnessTriggers, skills, commands, claudeMdSection }
  skills/          # SKILL.md contents
  commands/        # slash-command prompts
```

`opensddrag init --flow <slug>` then writes those files into the target project and registers the manifest. Non-SDD commands land under `.claude/commands/opsr/<slug>/` and are invoked as `/opsr:<slug>:<command>`.

---

## SDD Slash Commands

After `init` (SDD is the default pipeline), the following slash commands are available inside Claude Code (prefix `/opsr:`). Commands from other pipelines use `/opsr:<flow>:<command>` instead.

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

The Harness is a per-project rule-gate layer. Rules are injected into every agent session and enforced at phase gates. SDD ships with `on_spec` / `on_apply` / `on_verify` / `on_archive`; `add_rule` currently accepts those plus `always`.

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

### Built-in rules

`opensddrag init` (and `opensddrag-server init` for existing projects) seeds **`tdd-first`** into every project:

| Rule | Trigger | Severity | Purpose |
|---|---|---|---|
| `tdd-first` | `on_apply` | `error` | Apply is test-first (RED → GREEN → REFACTOR) per testable unit. Stack-agnostic — applies to pytest, vitest, jest, go test. Tasks with `metadata.test_exempt=true` plus a stated reason are exempt. |

### TDD discipline and test artifacts

Every scenario in a spec and every unit covered during apply is a first-class **`test` artifact** in the database (no separate table). The lifecycle is:

1. `/opsr:spec` Step 7 — the scenario-confirmation gate — creates one `test` artifact per confirmed WHEN/THEN (`level=scenario`, `test_status=pending`), linked to the spec via `implements`. The agent must STOP for user confirmation before creating them, even when scenarios look obvious.
2. `/opsr:tasks` Step 3 — for each testable unit in a task, creates a `test` artifact (`level=unit`, `test_status=pending`) and links it to the task via `implements` *before* `validate_artifact` runs. Tasks with no testable unit (prompt templates, SQL migrations without standalone logic) carry `metadata.test_exempt=true` plus a `## Reason` heading.
3. `/opsr:apply` Step 5 — the RED → GREEN → REFACTOR cycle, per unit:
   - **RED** — write a failing test using the project's native runner. Update `test_status` to `"failing"`. No production code yet.
   - **GREEN** — write the minimal production code to make it pass. Update `test_status` to `"passing"`.
   - **REFACTOR** — clean up while keeping the test green. `test_status` stays `"passing"`.
4. `/opsr:verify` Step 5 — recomputes scenario-level `test_status` from its linked unit tests (passing / failing / pending) and lists any non-exempt test that is not `"passing"` as a CRITICAL blocker. The verify report does not recommend `/opsr:archive` while blockers exist.

The `tdd-first` rule (seeded at `init`) blocks `apply` if a non-exempt task would be written without a failing test first. Use `/opsr:harness list` to inspect it, or `/opsr:harness disable tdd-first` if your project legitimately needs a different stance.

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

This starts PostgreSQL/pgvector on `localhost:54326`, the MCP + management API on `http://localhost:8000`, and the dashboard on [http://localhost:3001](http://localhost:3001). Dashboard login is `MANAGEMENT_API_TOKEN` (Compose default `123456`) — not an MCP API key.

**Local (development)**

```bash
cd mcp-server
cp .env.example .env
uv pip install -e .
opensddrag-server init          # run migrations + seed global SDD skills
opensddrag-server server start --transport sse --port 8000
```

The npm CLI is `opensddrag`. The Python server CLI is `opensddrag-server`. Do not mix them.

## License

MIT
