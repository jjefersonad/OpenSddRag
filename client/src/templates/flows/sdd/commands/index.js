export function getCommands(slug, serverUrl) {
  /**
   * Header for SDD artifact-management commands (propose, spec, design, tasks,
   * archive, explore, continue, status, search, sync, flow).
   * All data writes go to the MCP server; local file creation is forbidden.
   * Per REQ-007 the header MUST NOT enumerate MCP tool names — the agent discovers
   * tools via the MCP `tools/list` handshake. The header keeps the IMPORTANT block
   * for Claude Code compatibility and the STOP-if-not-connected instruction.
   */
  const artifactHeader = (name) => `> **IMPORTANT — ${name}**
> This command requires the **\`opensddrag\`** MCP server (${serverUrl}), configured in \`.mcp.json\`.
> All artifact reads/writes go through the OpenSddRag MCP tools. DO NOT create local files. DO NOT write markdown to disk.
> **If no OpenSddRag MCP tools are in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (\`docker compose up -d\`) and reload the project."
> **project_slug for every call: \`${slug}\`**

---
`;

  /**
   * Header for implementation-phase commands (apply, verify).
   * SDD planning artifacts are read from and traced via the MCP server; code
   * implementation writes local files using standard tools (Edit, Write, Bash).
   * Per REQ-007 the header MUST NOT enumerate MCP tool names.
   */
  const implementHeader = (name) => `> **IMPORTANT — ${name}**
> This command requires the **\`opensddrag\`** MCP server (${serverUrl}), configured in \`.mcp.json\`.
> SDD planning artifacts are read/traced via the OpenSddRag MCP tools. Code implementation writes local files using Edit, Write, Bash — this is expected and required.
> **If no OpenSddRag MCP tools are in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (\`docker compose up -d\`) and reload the project."
> **project_slug for every MCP call: \`${slug}\`**

---
`;

  /**
   * Header for harness-management commands (harness).
   * Project rules are stored in the MCP server's project_rules table.
   * No local file writes — all persistence is via the harness MCP tools.
   * Per REQ-007 the header MUST NOT enumerate MCP tool names.
   */
  const harnessHeader = (name) => `> **IMPORTANT — ${name}**
> This command requires the **\`opensddrag\`** MCP server (${serverUrl}), configured in \`.mcp.json\`.
> Harness rules are persisted in the MCP server's database. Do NOT write rule definitions to local files.
> **If no OpenSddRag MCP tools are in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (\`docker compose up -d\`) and reload the project."
> **project_slug for every call: \`${slug}\`**

---
`;

  /**
   * Standard pointer tail used by every command. Tells the agent to load
   * the corresponding skill (which holds the complete workflow) and follow it.
   * The skill is the single source of truth for MCP calls, templates, and steps.
   */
  const pointerTail = (skillName) => `
## Step 1 — Load the skill
Invoke the \`${skillName}\` skill (Claude Code auto-loads it from \`.claude/skills/${skillName}/SKILL.md\` via the slash command; OpenCode loads it from \`.opencode/skills/${skillName}/SKILL.md\` via the \`skill\` tool).
The skill contains the complete workflow — MCP calls, templates, examples, edge cases. Follow it verbatim and do not duplicate its steps here.
`;

  return [
    // ── /opsr:propose ────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "propose",
      content: `${artifactHeader("/opsr:propose")}## Purpose
Create a named change with a proposal artifact. This is the entry point for every new feature or change.
After this command, /opsr:spec and /opsr:design become available.

## Input
$ARGUMENTS = change name (kebab-case) or plain description. If plain description, derive a kebab-case name.
${pointerTail("opensddrag-propose")}`,
    },

    // ── /opsr:spec ──────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "spec",
      content: `${artifactHeader("/opsr:spec")}## Purpose
Create one or more spec artifacts for the capabilities listed in a proposal. Each capability in "New Capabilities" or "Modified Capabilities" gets its own spec artifact. Specs use SHALL/MUST language and must have Scenarios with WHEN/THEN format.

## Input
$ARGUMENTS = change name. If not provided, list proposals and ask.
${pointerTail("opensddrag-spec")}`,
    },

    // ── /opsr:design ────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "design",
      content: `${artifactHeader("/opsr:design")}## Purpose
Create a design document that captures technical decisions, architecture, trade-offs, and open questions. The design must be based on the proposal and spec artifacts already in the database.

## Input
$ARGUMENTS = change name.
${pointerTail("opensddrag-design")}`,
    },

    // ── /opsr:tasks ─────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "tasks",
      content: `${artifactHeader("/opsr:tasks")}## Purpose
Decompose the specs and design into atomic, verifiable task artifacts. Each task must map to one or more spec requirements (REQ-NNN) and be completable in under 4 hours. Tasks depend on BOTH specs AND design being in the database.

## Input
$ARGUMENTS = change name.
${pointerTail("opensddrag-tasks")}`,
    },

    // ── /opsr:apply ─────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "apply",
      content: `${implementHeader("/opsr:apply")}## Purpose
Implement tasks one by one, validating each against the spec acceptance criteria before marking done. Read ALL planning artifacts (proposal, specs, design) as context before implementing any task.

## Input
$ARGUMENTS = change name, or specific task name.
${pointerTail("opensddrag-apply")}`,
    },

    // ── /opsr:verify ────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "verify",
      content: `${implementHeader("/opsr:verify")}## Purpose
Validate the implementation against the spec requirements and design decisions. Produces a structured report with CRITICAL, WARNING, and SUGGESTION severity levels. Does NOT modify any artifacts — read-only operation.

## Input
$ARGUMENTS = change name.
${pointerTail("opensddrag-verify")}`,
    },

    // ── /opsr:sync ──────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "sync",
      content: `${artifactHeader("/opsr:sync")}## Purpose
Merge delta specs (ADDED/MODIFIED/REMOVED/RENAMED sections) into the main specs stored in the database. Delta specs are created by /opsr:spec for MODIFIED capabilities. After sync, the main spec reflects all changes. This is called automatically during /opsr:archive.

## Input
$ARGUMENTS = change name.
${pointerTail("opensddrag-sync")}`,
    },

    // ── /opsr:archive ───────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "archive",
      content: `${artifactHeader("/opsr:archive")}## Purpose
Finalize a completed change by archiving all its artifacts. Runs verification checks, syncs delta specs to main specs, then archives everything.

## Input
$ARGUMENTS = change name. If not provided, list active changes and ask.
${pointerTail("opensddrag-archive")}`,
    },

    // ── /opsr:explore ───────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "explore",
      content: `${artifactHeader("/opsr:explore")}## Purpose
Think through a problem, idea, or question WITHOUT implementing anything. Explore creates understanding before committing to a proposal. You may create OpenSddRag artifacts to capture insights, but NEVER write application code.

## Input
$ARGUMENTS = topic, question, or idea to explore.
${pointerTail("opensddrag-explore")}`,
    },

    // ── /opsr:continue ──────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "continue",
      content: `${artifactHeader("/opsr:continue")}## Purpose
Create the NEXT single artifact in the dependency chain for a change. Unlike /opsr:flow which creates all artifacts, this creates ONE artifact and stops. Dependency order: proposal → specs → design → tasks.

## Input
$ARGUMENTS = change name.
${pointerTail("opensddrag-continue")}`,
    },

    // ── /opsr:status ────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "status",
      content: `${artifactHeader("/opsr:status")}## Purpose
Show the current state of all in-progress changes for this project. Reads from the MCP server — no local files involved.

## Input
$ARGUMENTS = optional change name to show details for one change. If not provided, show all.
${pointerTail("opensddrag-status")}`,
    },

    // ── /opsr:flow ──────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "flow",
      content: `${artifactHeader("/opsr:flow")}## Purpose
Run the complete SDD flow end-to-end in a single session. Planning artifacts (proposal, specs, design, tasks) are saved to the database via MCP tools. Implementation code (Phase 5) is written locally using standard file tools (Edit, Write, Bash).

## Input
$ARGUMENTS = feature description or change name.
${pointerTail("opensddrag-flow")}`,
    },

    // ── /opsr:search ────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "search",
      content: `${artifactHeader("/opsr:search")}## Purpose
Search the SDD knowledge base using semantic similarity (pgvector). Use this BEFORE starting any new work to find existing specs, decisions, and past implementations.

## Input
$ARGUMENTS = natural language search query.
${pointerTail("opensddrag-search")}`,
    },

    // ── /opsr:harness ───────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "harness",
      content: `${harnessHeader("/opsr:harness")}## Purpose
Manage project harness rules: add new rules, list existing rules, and disable rules that are no longer needed. Harness rules are persistent behavioral constraints injected into every agent session via the working context and surfaced as phase-gate checklists at spec/apply/verify/archive.

## Input
$ARGUMENTS = one of: \`add\` (followed by rule fields or a natural-language description), \`list\` (show all rules), or \`disable <rule-name>\` (soft-delete by name). If empty, show the current rules list and ask.
${pointerTail("opensddrag-harness")}`,
    },
  ];
}
