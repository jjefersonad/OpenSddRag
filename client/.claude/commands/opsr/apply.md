> **IMPORTANT — /opsr:apply**
> This command requires the **`opensddrag`** MCP server (http://localhost:8000), configured in `.mcp.json`.
> SDD planning artifacts are read/traced via the OpenSddRag MCP tools. Code implementation writes local files using Edit, Write, Bash — this is expected and required.
> **If no OpenSddRag MCP tools are in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (`docker compose up -d`) and reload the project."
> **project_slug for every MCP call: `opensddrag`**

---
## Purpose
Implement tasks one by one, validating each against the spec acceptance criteria before marking done. Read ALL planning artifacts (proposal, specs, design) as context before implementing any task.

## Input
$ARGUMENTS = change name, or specific task name.

## Step 1 — Load the skill
Invoke the `opensddrag-apply` skill (Claude Code auto-loads it from `.claude/skills/opensddrag-apply/SKILL.md` via the slash command; OpenCode loads it from `.opencode/skills/opensddrag-apply/SKILL.md` via the `skill` tool).
The skill contains the complete workflow — MCP calls, templates, examples, edge cases. Follow it verbatim and do not duplicate its steps here.
