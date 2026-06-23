> **IMPORTANT — /opsr:verify**
> This command requires the **`opensddrag`** MCP server (http://localhost:8000), configured in `.mcp.json`.
> SDD planning artifacts are read/traced via the OpenSddRag MCP tools. Code implementation writes local files using Edit, Write, Bash — this is expected and required.
> **If no OpenSddRag MCP tools are in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (`docker compose up -d`) and reload the project."
> **project_slug for every MCP call: `opensddrag`**

---
## Purpose
Validate the implementation against the spec requirements and design decisions. Produces a structured report with CRITICAL, WARNING, and SUGGESTION severity levels. Does NOT modify any artifacts — read-only operation.

## Input
$ARGUMENTS = change name.

## Step 1 — Load the skill
Invoke the `opensddrag-verify` skill (Claude Code auto-loads it from `.claude/skills/opensddrag-verify/SKILL.md` via the slash command; OpenCode loads it from `.opencode/skills/opensddrag-verify/SKILL.md` via the `skill` tool).
The skill contains the complete workflow — MCP calls, templates, examples, edge cases. Follow it verbatim and do not duplicate its steps here.
