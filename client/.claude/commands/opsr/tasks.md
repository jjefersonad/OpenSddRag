> **IMPORTANT — /opsr:tasks**
> This command requires the **`opensddrag`** MCP server (http://localhost:8000), configured in `.mcp.json`.
> All artifact reads/writes go through the OpenSddRag MCP tools. DO NOT create local files. DO NOT write markdown to disk.
> **If no OpenSddRag MCP tools are in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (`docker compose up -d`) and reload the project."
> **project_slug for every call: `opensddrag`**

---
## Purpose
Decompose the specs and design into atomic, verifiable task artifacts. Each task must map to one or more spec requirements (REQ-NNN) and be completable in under 4 hours. Tasks depend on BOTH specs AND design being in the database.

## Input
$ARGUMENTS = change name.

## Step 1 — Load the skill
Invoke the `opensddrag-tasks` skill (Claude Code auto-loads it from `.claude/skills/opensddrag-tasks/SKILL.md` via the slash command; OpenCode loads it from `.opencode/skills/opensddrag-tasks/SKILL.md` via the `skill` tool).
The skill contains the complete workflow — MCP calls, templates, examples, edge cases. Follow it verbatim and do not duplicate its steps here.
