> **IMPORTANT — /opsr:design**
> This command requires the **`opensddrag`** MCP server (http://localhost:8000), configured in `.mcp.json`.
> All artifact reads/writes go through the OpenSddRag MCP tools. DO NOT create local files. DO NOT write markdown to disk.
> **If no OpenSddRag MCP tools are in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (`docker compose up -d`) and reload the project."
> **project_slug for every call: `opensddrag`**

---
## Purpose
Create a design document that captures technical decisions, architecture, trade-offs, and open questions. The design must be based on the proposal and spec artifacts already in the database.

## Input
$ARGUMENTS = change name.

## Step 1 — Load the skill
Invoke the `opensddrag-design` skill (Claude Code auto-loads it from `.claude/skills/opensddrag-design/SKILL.md` via the slash command; OpenCode loads it from `.opencode/skills/opensddrag-design/SKILL.md` via the `skill` tool).
The skill contains the complete workflow — MCP calls, templates, examples, edge cases. Follow it verbatim and do not duplicate its steps here.
