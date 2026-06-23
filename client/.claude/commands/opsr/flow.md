> **IMPORTANT — /opsr:flow**
> This command requires the **`opensddrag`** MCP server (http://localhost:8000), configured in `.mcp.json`.
> All artifact reads/writes go through the OpenSddRag MCP tools. DO NOT create local files. DO NOT write markdown to disk.
> **If no OpenSddRag MCP tools are in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (`docker compose up -d`) and reload the project."
> **project_slug for every call: `opensddrag`**

---
## Purpose
Run the complete SDD flow end-to-end in a single session. Planning artifacts (proposal, specs, design, tasks) are saved to the database via MCP tools. Implementation code (Phase 5) is written locally using standard file tools (Edit, Write, Bash).

## Input
$ARGUMENTS = feature description or change name.

## Step 1 — Load the skill
Invoke the `opensddrag-flow` skill (Claude Code auto-loads it from `.claude/skills/opensddrag-flow/SKILL.md` via the slash command; OpenCode loads it from `.opencode/skills/opensddrag-flow/SKILL.md` via the `skill` tool).
The skill contains the complete workflow — MCP calls, templates, examples, edge cases. Follow it verbatim and do not duplicate its steps here.
