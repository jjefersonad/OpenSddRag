/**
 * OpenCode command templates
 * Installed to .opencode/commands/opsr/ when OpenCode is selected.
 * Uses a compact openCodeHeader() (project_slug only) instead of the Claude Code
 * IMPORTANT/tool-list/STOP block — MCP tools are auto-available in OpenCode.
 *
 * Per the command-skill-separation-contract, every command is a pure pointer:
 * Purpose + Input + a single "Load the skill" step. The complete workflow
 * (MCP calls, templates, examples, edge cases) lives in the matching
 * opensddrag-<name> skill. Do NOT add workflow steps here.
 */

export function getOpenCodeCommands(slug, _serverUrl) {
  const fm = (description) => `---\ndescription: ${description}\n---\n\n`;

  const openCodeHeader = () => `> **project_slug for every call:** \`${slug}\`\n\n---\n\n\n`;

  /**
   * Standard pointer tail for OpenCode commands. Tells the agent to load the
   * corresponding skill (the single source of truth for the workflow) via the
   * `skill` tool and follow it. No workflow detail is duplicated here.
   */
  const pointerTail = (skillName) => `
## Step 1 — Load the skill
Invoke the \`${skillName}\` skill (OpenCode loads it from \`.opencode/skills/${skillName}/SKILL.md\` via the \`skill\` tool).
The skill contains the complete workflow — MCP calls, templates, examples, edge cases. Follow it verbatim and do not duplicate its steps here.
`;

  return [
    // ── /opsr:propose ──────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "propose",
      content: `${fm("Create a named change proposal")}${openCodeHeader()}## Purpose
Create a named change with a proposal artifact. This is the entry point for every new feature or change.
The proposal defines WHY, WHAT changes, WHICH capabilities are affected, and the IMPACT.
After this command, /opsr:spec and /opsr:design become available.

## Input
$ARGUMENTS = change name (kebab-case) or plain description. If plain description, derive a kebab-case name.
${pointerTail("opensddrag-propose")}`,
    },

    // ── /opsr:spec ─────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "spec",
      content: `${fm("Write capability specs with requirements and scenarios")}${openCodeHeader()}## Purpose
Create one or more spec artifacts for the capabilities listed in a proposal.
Each capability in "New Capabilities" or "Modified Capabilities" gets its own spec artifact.
Specs use SHALL/MUST language and must have Scenarios with WHEN/THEN format.

## Input
$ARGUMENTS = change name. If not provided, list proposals and ask.
${pointerTail("opensddrag-spec")}`,
    },

    // ── /opsr:design ───────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "design",
      content: `${fm("Document technical decisions and architecture")}${openCodeHeader()}## Purpose
Create a design document that captures technical decisions, architecture, trade-offs, and open questions.
The design must be based on the proposal and spec artifacts already in the database.

## Input
$ARGUMENTS = change name.
${pointerTail("opensddrag-design")}`,
    },

    // ── /opsr:tasks ────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "tasks",
      content: `${fm("Break a design into atomic implementation tasks")}${openCodeHeader()}## Purpose
Decompose the specs and design into atomic, verifiable task artifacts.
Each task must map to one or more spec requirements (REQ-NNN) and be completable in under 4 hours.
Tasks depend on BOTH specs AND design being in the database.

## Input
$ARGUMENTS = change name.
${pointerTail("opensddrag-tasks")}`,
    },

    // ── /opsr:apply ────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "apply",
      content: `${fm("Implement the next pending task")}${openCodeHeader()}## Purpose
Implement tasks one by one, validating each against the spec acceptance criteria before marking done.
Read ALL planning artifacts (proposal, specs, design) as context before implementing any task.

## Input
$ARGUMENTS = change name, or specific task name.
${pointerTail("opensddrag-apply")}`,
    },

    // ── /opsr:verify ────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "verify",
      content: `${fm("Validate implementation against spec requirements")}${openCodeHeader()}## Purpose
Validate the implementation against the spec requirements and design decisions.
Produces a structured report with CRITICAL, WARNING, and SUGGESTION severity levels.
Does NOT modify any artifacts — read-only operation.

## Input
$ARGUMENTS = change name.
${pointerTail("opensddrag-verify")}`,
    },

    // ── /opsr:sync ──────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "sync",
      content: `${fm("Merge delta specs into main specs")}${openCodeHeader()}## Purpose
Merge delta specs (ADDED/MODIFIED/REMOVED/RENAMED sections) into the main specs stored in the database.
Delta specs are created by /opsr:spec for MODIFIED capabilities.
After sync, the main spec reflects all changes. This is called automatically during /opsr:archive.

## Input
$ARGUMENTS = change name.
${pointerTail("opensddrag-sync")}`,
    },

    // ── /opsr:archive ───────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "archive",
      content: `${fm("Finalize and archive a completed change")}${openCodeHeader()}## Purpose
Finalize a completed change by archiving all its artifacts.
Runs verification checks, syncs delta specs to main specs, then archives everything.

## Input
$ARGUMENTS = change name. If not provided, list active changes and ask.
${pointerTail("opensddrag-archive")}`,
    },

    // ── /opsr:explore ───────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "explore",
      content: `${fm("Investigate a problem without implementing anything")}${openCodeHeader()}## Purpose
Think through a problem, idea, or question WITHOUT implementing anything.
Explore creates understanding before committing to a proposal.
You may create OpenSddRag artifacts to capture insights, but NEVER write application code.

## Input
$ARGUMENTS = topic, question, or idea to explore.
${pointerTail("opensddrag-explore")}`,
    },

    // ── /opsr:continue ─────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "continue",
      content: `${fm("Create the next artifact in the SDD dependency chain")}${openCodeHeader()}## Purpose
Create the NEXT single artifact in the dependency chain for a change.
Unlike /opsr:flow which creates all artifacts, this creates ONE artifact and stops.
Dependency order: proposal → specs → design → tasks.

## Input
$ARGUMENTS = change name.
${pointerTail("opensddrag-continue")}`,
    },

    // ── /opsr:status ────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "status",
      content: `${fm("Show state of all in-progress changes")}${openCodeHeader()}## Purpose
Show the current state of all in-progress changes for this project.
Reads from the MCP server — no local files involved.

## Input
$ARGUMENTS = optional change name to show details for one change. If not provided, show all.
${pointerTail("opensddrag-status")}`,
    },

    // ── /opsr:flow ──────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "flow",
      content: `${fm("Run the complete SDD flow end-to-end")}${openCodeHeader()}## Purpose
Run the complete SDD flow end-to-end in a single session.
ALL planning artifacts are saved to the database via MCP tools; implementation code is written locally.

## Input
$ARGUMENTS = feature description or change name.
${pointerTail("opensddrag-flow")}`,
    },

    // ── /opsr:search ────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "search",
      content: `${fm("Semantic search over specs and past work")}${openCodeHeader()}## Purpose
Search the SDD knowledge base using semantic similarity (pgvector).
Use this BEFORE starting any new work to find existing specs, decisions, and past implementations.

## Input
$ARGUMENTS = natural language search query.
${pointerTail("opensddrag-search")}`,
    },

    // ── /opsr:harness ───────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "harness",
      content: `${fm("Manage persistent project rules (add, list, disable)")}${openCodeHeader()}## Purpose
Manage project harness rules: add new rules, list existing rules, and disable rules that are no longer needed.
Harness rules are persistent behavioral constraints injected into every agent session and surfaced as phase-gate checklists at spec/apply/verify/archive.

## Input
$ARGUMENTS = one of: \`add\` (followed by rule fields or a natural-language description), \`list\` (show all rules), or \`disable <rule-name>\` (soft-delete by name). If empty, show the current rules list and ask.
${pointerTail("opensddrag-harness")}`,
    },
  ];
}
