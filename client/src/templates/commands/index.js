export function getCommands(slug, serverUrl) {
  /**
   * Header for SDD artifact-management commands (propose, spec, design, tasks,
   * archive, explore, continue, status, search, sync, flow).
   * All data writes go to the MCP server; local file creation is forbidden.
   */
  const artifactHeader = (name) => `> **IMPORTANT — ${name}**
> This command requires the **\`opensddrag\`** MCP server (${serverUrl}), configured in \`.mcp.json\`.
> MCP tools provided by this server: \`create_artifact\`, \`read_artifact\`, \`list_artifacts\`, \`update_artifact\`, \`validate_artifact\`, \`link_artifacts\`, \`get_relationships\`, \`search_semantic\`, \`recall_episodes\`, \`get_working_context\`, \`update_working_context\`, \`record_trace\`, \`get_harness_checklist\`

> **If these tools are NOT in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (\`docker compose up -d\`) and reload the project."
> All artifact reads/writes go through these MCP tools. DO NOT create local files. DO NOT write markdown to disk.
> **project_slug for every call: \`${slug}\`**

---

`;

  /**
   * Header for implementation-phase commands (apply, verify).
   * SDD planning artifacts are read from and traced via the MCP server; code
   * implementation writes local files using standard tools (Edit, Write, Bash).
   */
  const implementHeader = (name) => `> **IMPORTANT — ${name}**
> This command requires the **\`opensddrag\`** MCP server (${serverUrl}), configured in \`.mcp.json\`.
> MCP tools provided by this server: \`read_artifact\`, \`list_artifacts\`, \`update_artifact\`, \`get_relationships\`, \`search_semantic\`, \`recall_episodes\`, \`get_working_context\`, \`update_working_context\`, \`record_trace\`, \`get_harness_checklist\`
> **If these tools are NOT in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (\`docker compose up -d\`) and reload the project."
> SDD planning artifacts are read/traced via these MCP tools. Code implementation writes local files using Edit, Write, Bash — this is expected and required.
> **project_slug for every MCP call: \`${slug}\`**

---
`;

  /**
   * Header for harness-management commands (harness).
   * Project rules are stored in the MCP server's project_rules table.
   * No local file writes — all persistence is via the harness MCP tools.
   */
  const harnessHeader = (name) => `> **IMPORTANT — ${name}**
> This command requires the **\`opensddrag\`** MCP server (${serverUrl}), configured in \`.mcp.json\`.
> MCP tools provided by this server: \`add_rule\`, \`list_rules\`, \`get_harness_checklist\`, \`get_working_context\`, \`record_trace\`
> **If these tools are NOT in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (\`docker compose up -d\`) and reload the project."
> Harness rules are persisted in the MCP server's database. Do NOT write rule definitions to local files.
> **project_slug for every call: \`${slug}\`**

---
`;

  /**
   * Reusable step block that calls `get_harness_checklist(trigger=...)` and
   * presents the results as a phase-gate checklist. Injected into `/opsr:apply`,
   * `/opsr:verify`, `/opsr:archive`, and `/opsr:spec` per spec
   * `harness-engineering-harness-checklist-spec` (REQ-002, REQ-003).
   *
   * Behavior:
   * - If the checklist is empty, print "No harness rules for this trigger." and
   *   continue normally.
   * - If the checklist has error-severity rules, the agent MUST confirm each
   *   one is satisfied before proceeding to the next step.
   * - Warning-severity rules are presented as advisory (SHOULD complete).
   *
   * @param {string} trigger - One of: "on_apply", "on_verify", "on_archive", "on_spec"
   * @param {string} gateLabel - Short human-readable label for the gate, e.g. "Marking task archived"
   * @returns {string} Markdown step content
   */
  const harnessChecklistStep = (trigger, gateLabel) => `## Step — Harness checklist (${trigger})
Call MCP tool to load all enabled harness rules for the \`${trigger}\` trigger:
\`get_harness_checklist(trigger="${trigger}", project_slug="${slug}")\`

Process the response as follows:
- **If the result is an empty array \`[]\`** → output "No harness rules for this trigger." and continue to the next step.
- **If any rule has \`severity="error"\`** → present it as:
  \`\`\`
  MUST complete before proceeding (${gateLabel}):
  - [<name>] <instruction>
  \`\`\`
  Then \`STOP\` and wait for the agent/user to confirm each error-severity rule has been satisfied before continuing.
- **If any rule has \`severity="warning"\`** → present it as:
  \`\`\`
  SHOULD complete:
  - [<name>] <instruction>
  \`\`\`
  These are advisory; proceed if the agent judges them satisfied, otherwise complete them first.
- **If any rule has \`severity="info"\`** → present it inline as "Info: [<name>] <instruction>"; proceed normally.
- Rules are returned sorted error-first then by name; preserve that order when displaying.
- This step must run BEFORE the next phase-gate step (archiving the task, finalizing verification, archiving change artifacts, or saving the spec to the database).

`;

  return [
    // ── <opsr:propose ───────────────────────────────────────────────────────────
    {
      folder: "opsr",
      folder: "opsr",
      name: "propose",
      content: `${artifactHeader("/opsr:propose")}## Purpose
Create a named change with a proposal artifact. This is the entry point for every new feature or change.
The proposal defines WHY, WHAT changes, WHICH capabilities are affected, and the IMPACT.
After this command, /opsr:spec and /opsr:design become available.

## Input
$ARGUMENTS = change name (kebab-case) or plain description. If plain description, derive a kebab-case name.

## Step 1 — Derive change name
If $ARGUMENTS is a plain description (contains spaces), convert to kebab-case.
Example: "add user authentication" → "add-user-authentication"

## Step 2 — Search for existing work (avoid duplication)
Call MCP tool:
\`search_semantic(query="$ARGUMENTS", project_slug="${slug}", limit=5)\`
If relevant artifacts are found, show them and ask the user to confirm this is new work.

## Step 3 — Write the proposal content
Compose the following structure (do NOT skip any section):

\`\`\`markdown
# <change-name>

## Why
[1-2 sentences on the problem or opportunity being addressed]

## What Changes
- [Specific change 1]
- [Specific change 2]
- **BREAKING** [Breaking change if any]

## Capabilities
### New Capabilities
- [capability-name] — brief description

### Modified Capabilities
- [existing-capability] — what changes

## Impact
[Affected code, APIs, dependencies, systems]
\`\`\`

## Step 4 — Save proposal to database
Call MCP tool:
\`create_artifact(name="<change-name>-proposal", type="proposal", content="<full proposal markdown>", metadata={"change_name": "<change-name>", "status_phase": "planning"}, project_slug="${slug}")\`
Note the returned artifact ID.

## Step 5 — Create spec drafts for each capability
Parse the "## Capabilities" section. For each capability listed in "New Capabilities" or "Modified Capabilities":
1. Check if a spec for this capability already exists:
\`read_artifact(name="<change-name>-<capability-name>-spec", project_slug="${slug}")\`
If it exists and is not empty, skip creating a draft.

2. If no spec exists, create a draft spec:

**IMPORTANT: copy the template content VERBATIM into the \`content\` parameter — do NOT replace [TODO] markers with generated requirements, scenarios, or domain-specific rules (e.g., JWT rules, database schemas, auth flows). This step is scaffolding only; actual content is added by /opsr:spec.**

\`create_artifact(name="<change-name>-<capability-name>-spec", type="spec", status="draft", content="# <capability-name> Specification

[TODO: Define purpose, requirements, and scenarios for this capability]

## Purpose
[TODO: Describe what this capability enables]

## Requirements
[TODO: List requirements with REQ-NNN format]

### Requirement: <REQ-001>
[TODO: Describe requirement using SHALL/MUST language]

#### Scenario: <Name>
- **WHEN** [condition]
- **THEN** [expected outcome]", metadata={"change_name": "<change-name>", "capability": "<capability-name>", "is_delta": true}, project_slug="${slug}")\`

## Step 6 — Create design skeleton
Create a draft design document:

**IMPORTANT: copy the template content VERBATIM — do NOT replace [TODO] markers with generated technical decisions, architecture choices, or risk assessments. Design content is added by /opsr:design.**

\`create_artifact(name="<change-name>-design", type="design", status="draft", content="# Design: <change-name>

[TODO: Document technical decisions, architecture, trade-offs]

## Context
[TODO: Background and constraints]

## Goals / Non-Goals
**Goals:**
- [Goal 1]

**Non-Goals:**
- [Non-goal 1]

## Decisions
### Decision: <Title>
**Chosen:** [What was chosen]
**Alternatives:**
- [Alternative 1] — rejected because [reason]

## Architecture
[TODO: Components and data flow]

## Risks / Trade-offs
| Risk | Mitigation |
|------|------------|
| [Risk] | [Mitigation] |

## Open Questions
- [ ] [Question]
", metadata={"change_name": "<change-name>"}, project_slug="${slug}")\`

## Step 7 — Record the action
Call MCP tool:
\`record_trace(action="propose", result_summary="Created proposal: <change-name>-proposal", project_slug="${slug}")\`

## Step 8 — Show what is now available
Tell the user:
- "Proposal saved with full scaffolding. The following commands are now available:"
- \`/opsr:spec <change-name>\` — formalize requirements (draft specs already created for each capability)
- \`/opsr:design <change-name>\` — document technical approach (draft design already created)
- Or run \`/opsr:flow <change-name>\` to continue the full flow automatically.
`,
    },

    // ── /opsr:spec ─────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "spec",
      content: `${artifactHeader("/opsr:spec")}## Purpose
Create one or more spec artifacts for the capabilities listed in a proposal.
Each capability in "New Capabilities" or "Modified Capabilities" gets its own spec artifact.
Specs use SHALL/MUST language and must have Scenarios with WHEN/THAN format.

## Input
$ARGUMENTS = change name. If not provided, list proposals and ask.

## Step 1 — Read the proposal from the database
Call MCP tool:
\`list_artifacts(type="proposal", project_slug="${slug}")\`
Then read the selected proposal:
\`read_artifact(name="<change-name>-proposal", project_slug="${slug}")\`

## Step 2 — Identify capabilities from the proposal
Parse the "## Capabilities" section. Each capability in "New Capabilities" and "Modified Capabilities" needs a spec.

**New capability** → create a full spec (Purpose + Requirements + Scenarios)
**Modified capability** → check if a main spec exists first:
\`search_semantic(query="<capability-name> spec", project_slug="${slug}", limit=3)\`
If main spec exists → create a DELTA spec with ADDED/MODIFIED/REMOVED/RENAMED sections.
If no main spec → create BOTH:
1. The main spec with metadata={"capability": "<capability-name>", "is_delta": false}
2. The delta spec with metadata={"change_name": "<change-name>", "capability": "<capability-name>", "is_delta": true}

## Step 3 — Write spec content for EACH capability

### Full spec structure (new capabilities):
\`\`\`markdown
# <capability-name> Specification

## Purpose
[High-level description of this capability]

## Requirements

### Requirement: <REQ-001 Name>
[Description using SHALL/MUST language]

#### Scenario: <Happy path name>
- **WHEN** [condition]
- **THEN** [expected outcome]

#### Scenario: <Edge case name>
- **WHEN** [edge condition]
- **THEN** [expected outcome]

### Requirement: <REQ-002 Name>
[Description]

#### Scenario: <Name>
- **WHEN** [condition]
- **THEN** [outcome]
\`\`\`

### Delta spec structure (modified capabilities):
\`\`\`markdown
# <capability-name> Specification — Delta

## ADDED Requirements
### Requirement: <New requirement name>
[Full requirement with scenarios]

## MODIFIED Requirements
### Requirement: <Existing requirement name>
[Updated requirement — include FULL updated text with all scenarios]

## REMOVED Requirements
### Requirement: <Removed requirement name>
**Reason:** [Why this is being removed]
**Migration:** [How consumers should migrate]

## RENAMED Requirements
- FROM: \`### Requirement: Old Name\`
- TO: \`### Requirement: New Name\`
\`\`\`

${harnessChecklistStep("on_spec", "Saving specs to the database")}
## Step 4 — Save each spec to the database
For each capability spec:
\`create_artifact(name="<change-name>-<capability-name>-spec", type="spec", content="<full spec markdown>", metadata={"change_name": "<change-name>", "capability": "<capability-name>", "is_delta": true/false}, project_slug="${slug}")\`

## Step 5 — Link each spec to the proposal
\`link_artifacts(source_name="<spec-name>", target_name="<change-name>-proposal", relationship_type="implements", project_slug="${slug}")\`

## Step 6 — Validate each spec
\`validate_artifact(name="<spec-name>", project_slug="${slug}")\`
Fix any validation errors before continuing.

## Step 7 — Record the action
\`record_trace(action="spec", result_summary="Created specs for: <capability-list>", project_slug="${slug}")\`

## Step 8 — Show what is now available
- "Specs saved. You can now run:"
- \`/opsr:design <change-name>\` — document technical decisions
`,
    },

    // ── /opsr:design ───────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "design",
      content: `${artifactHeader("/opsr:design")}## Purpose
Create a design document that captures technical decisions, architecture, trade-offs, and open questions.
The design must be based on the proposal and spec artifacts already in the database.

## Input
$ARGUMENTS = change name.

## Step 1 — Read proposal and all specs from the database
\`read_artifact(name="<change-name>-proposal", project_slug="${slug}")\`
\`list_artifacts(type="spec", project_slug="${slug}")\`
Read each spec linked to this change:
\`get_relationships(name="<change-name>-proposal", project_slug="${slug}")\`

## Step 2 — Search for related prior designs
\`search_semantic(query="<change topic> design decisions", project_slug="${slug}", limit=3)\`
Use findings as context — don't duplicate prior work.

## Step 3 — Write the design content
\`\`\`markdown
# Design: <change-name>

## Context
[Background, current state, constraints that shaped this design]

## Goals / Non-Goals
**Goals:**
- [What this design achieves]

**Non-Goals:**
- [What this design deliberately does NOT address]

## Decisions

### Decision: <Title>
**Chosen:** [What was chosen and why]
**Alternatives considered:**
- [Alternative 1] — rejected because [reason]
- [Alternative 2] — rejected because [reason]

### Decision: <Title>
...

## Architecture
[Components, data flow, integration points — use ASCII diagrams if helpful]

## Risks / Trade-offs
| Risk | Mitigation |
|------|------------|
| [Risk] | [Mitigation] |

## Migration Plan
[Deployment steps, backward compatibility, rollback plan]

## Open Questions
- [ ] [Question that still needs resolution]
\`\`\`

## Step 4 — Save design to database
\`create_artifact(name="<change-name>-design", type="design", content="<full design markdown>", metadata={"change_name": "<change-name>"}, project_slug="${slug}")\`

## Step 5 — Link design to proposal
\`link_artifacts(source_name="<change-name>-design", target_name="<change-name>-proposal", relationship_type="depends_on", project_slug="${slug}")\`

## Step 6 — Record and show next steps
\`record_trace(action="design", result_summary="Created design: <change-name>-design", project_slug="${slug}")\`
Tell the user: "Design saved. Run \`<opsr:tasks <change-name>\` to decompose into tasks."
`,
    },

    // ── <opsr:tasks ────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "tasks",
      content: `${artifactHeader("/opsr:tasks")}## Purpose
Decompose the specs and design into atomic, verifiable task artifacts.
Each task must map to one or more spec requirements (REQ-NNN) and be completable in under 4 hours.
Tasks depend on BOTH specs AND design being in the database.

## Input
$ARGUMENTS = change name.

## Step 1 — Read all planning artifacts from the database
\`read_artifact(name="<change-name>-proposal", project_slug="${slug}")\`
\`read_artifact(name="<change-name>-design", project_slug="${slug}")\`
Get all specs for this change:
\`get_relationships(name="<change-name>-proposal", project_slug="${slug}")\`
Read each linked spec artifact.

## Step 2 — Plan task groups from the design and specs
Group tasks by logical phase. Each task must have:
- A clear **Goal** (what it accomplishes)
- **Acceptance criteria** referencing spec REQ-NNN items (not vague)
- **Dependencies** on other tasks (if any)
- Estimated effort: < 4 hours

## Step 3 — Create each task artifact in the database
For each task (name as \`<change-name>-task-<group>-<N>\`):
\`create_artifact(name="<change-name>-task-<group>-<N>", type="task", content="## Goal\\n<what this task accomplishes>\\n\\n## Acceptance Criteria\\n- [ ] REQ-NNN: <criterion>\\n- [ ] <criterion>\\n\\n## Dependencies\\n- <other task name or 'none'>", metadata={"change_name": "<change-name>", "group": "<group-name>", "order": <N>}, project_slug="${slug}")\`

## Step 4 — Link each task to its spec(s)
\`link_artifacts(source_name="<task-name>", target_name="<spec-name>", relationship_type="implements", project_slug="${slug}")\`

## Step 5 — Update working context with the task list
\`update_working_context(context={"change_name": "<change-name>", "tasks": ["<task-1>", "<task-2>", "..."], "current_task": null}, project_slug="${slug}")\`

## Step 6 — Record and show next steps
\`record_trace(action="tasks", result_summary="Created <N> tasks for <change-name>", project_slug="${slug}")\`
Show the full task list with names and goals.
Tell the user: "Tasks saved. Run \`<opsr:apply <change-name>\` to start implementing."
`,
    },

    // ── <opsr:apply ────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "apply",
      content: `${implementHeader("/opsr:apply")}## Purpose
Implement tasks one by one, validating each against the spec acceptance criteria before marking done.
Read ALL planning artifacts (proposal, specs, design) as context before implementing any task.

## Input
$ARGUMENTS = change name, or specific task name.

## Step 1 — Load full planning context from the database
\`get_working_context(project_slug="${slug}")\`
\`read_artifact(name="<change-name>-proposal", project_slug="${slug}")\`
\`read_artifact(name="<change-name>-design", project_slug="${slug}")\`
Get and read all specs linked to this change.

## Step 2 — List pending tasks in order
\`list_artifacts(type="task", status="draft", project_slug="${slug}")\`
AND
\`list_artifacts(type="task", status="active", project_slug="${slug}")\`
Combine both results. Prioritize tasks with status="active" (resuming interrupted session), then status="draft" in dependency order. Filter tasks for this change using metadata.change_name.

## Step 3 — Select next task
If $ARGUMENTS specifies a task name, use it.
Otherwise:
1. First, check for tasks with status="active" (resuming interrupted session)
2. If no active tasks, pick the first draft task whose dependencies are all archived (done)

Read the task:
\`read_artifact(name="<task-name>", project_slug="${slug}")\`

## Step 4 — Mark task as active in database
\`update_artifact(name="<task-name>", status="active", project_slug="${slug}")\`
Update working context:
\`update_working_context(context={"current_task": "<task-name>"}, project_slug="${slug}")\`

## Step 5 — Implement the task
Implement the code changes required by the task.
The implementation MUST satisfy all acceptance criteria from the task's "## Acceptance Criteria" section.
Pause and ask the user if any requirement is unclear — do not guess.

## Step 6 — Validate against spec requirements
For each acceptance criterion (REQ-NNN) in the task:
- Confirm the implementation satisfies the requirement
- Verify no spec scenarios are broken

${harnessChecklistStep("on_apply", "Marking task archived")}
## Step 7 — Mark task as done in database
\`update_artifact(name="<task-name>", status="archived", project_slug="${slug}")\`

## Step 8 — Record and check remaining tasks
\`record_trace(action="apply_task", result_summary="Completed task: <task-name>", artifact_id="<artifact-id>", project_slug="${slug}")\`
\`list_artifacts(type="task", status="draft", project_slug="${slug}")\`
- If tasks remain: "Task complete. Run \`<opsr:apply <change-name>\` for the next task."
- If all done: "All tasks complete. Run \`<opsr:verify <change-name>\` to validate, then \`<opsr:archive <change-name>\`."
`,
    },

    // ── <opsr:verify ────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "verify",
      content: `${implementHeader("/opsr:verify")}## Purpose
Validate the implementation against the spec requirements and design decisions.
Produces a structured report with CRITICAL, WARNING, and SUGGESTION severity levels.
Does NOT modify any artifacts — read-only operation.

## Input
$ARGUMENTS = change name.

## Step 1 — Load all artifacts from the database
\`read_artifact(name="<change-name>-proposal", project_slug="${slug}")\`
\`read_artifact(name="<change-name>-design", project_slug="${slug}")\`
Get all specs and tasks for this change:
\`get_relationships(name="<change-name>-proposal", project_slug="${slug}")\`
Read each linked spec and task artifact.

## Step 2 — Verify COMPLETENESS
Check task completion:
\`list_artifacts(type="task", status="draft", project_slug="${slug}")\`
- If pending tasks exist → **CRITICAL: Tasks not complete**

Extract all requirements (REQ-NNN) from specs.
For each requirement, search the codebase for implementation evidence.
- If requirement has no implementation evidence → **CRITICAL: Requirement not implemented**

## Step 3 — Verify CORRECTNESS
For each spec scenario (WHEN/THAN blocks):
- Search the codebase for test coverage or implementation of the scenario condition
- If scenario has no coverage → **WARNING: Scenario not covered**

## Step 4 — Verify COHERENCE
Extract decisions from the "## Decisions" section of the design.
For each decision:
- Check if the implementation follows the chosen approach
- If implementation deviates from a decision → **SUGGESTION: Possible deviation from design**

${harnessChecklistStep("on_verify", "Declaring verification complete")}
## Step 5 — Generate report
Output a structured report:

\`\`\`
## Verification Report: <change-name>

### Summary
| Dimension    | Status |
|--------------|--------|
| Completeness | ✓/✗   |
| Correctness  | ✓/✗   |
| Coherence    | ✓/✗   |

### CRITICAL Issues
- [Issue description]

### WARNING Issues
- [Issue description]

### SUGGESTIONS
- [Issue description]

### Assessment
[READY TO ARCHIVE | ISSUES MUST BE FIXED BEFORE ARCHIVING]
\`\`\`

## Step 6 — Record the verification
\`record_trace(action="verify", result_summary="Verification: <PASS/FAIL> — <N> critical, <N> warnings", project_slug="${slug}")\`
`,
    },

    // ── <opsr:sync ──────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "sync",
      content: `${artifactHeader("/opsr:sync")}## Purpose
Merge delta specs (ADDED/MODIFIED/REMOVED/RENAMED sections) into the main specs stored in the database.
Delta specs are created by /opsr:spec for MODIFIED capabilities.
After sync, the main spec reflects all changes. This is called automatically during /archive.

## Input
$ARGUMENTS = change name.

## Step 1 — Find delta specs for this change
\`list_artifacts(type="spec", project_slug="${slug}")\`
Filter specs where metadata.change_name = "<change-name>" AND metadata.is_delta = true.

## Step 2 — For each delta spec, find the main spec
Search for the main (non-delta) spec for the same capability:
\`search_semantic(query="<capability-name> spec", project_slug="${slug}", limit=5)\`
Find the spec where metadata.is_delta = false (or not set) for the same capability.

## Step 3 — Apply delta operations to the main spec
Read both delta and main spec:
\`read_artifact(name="<delta-spec-name>", project_slug="${slug}")\`
\`read_artifact(name="<main-spec-name>", project_slug="${slug}")\`

Apply each section from the delta:

**## ADDED Requirements:**
- Find or confirm the requirement does NOT exist in main spec
- Append the new requirement (with all scenarios) to the main spec

**## MODIFIED Requirements:**
- Find the requirement in main spec by name
- Apply ONLY the changed parts (add new scenarios, update descriptions)
- Do NOT wholesale replace — apply partial updates intelligently

**## REMOVED Requirements:**
- Find the requirement in main spec by name
- Remove the entire requirement block
- The Reason and Migration from delta should be noted in a comment

**## RENAMED Requirements:**
- Find FROM name in main spec
- Change the heading to TO name

## Step 4 — Save the updated main spec to database
\`update_artifact(name="<main-spec-name>", content="<merged spec content>", project_slug="${slug}")\`

## Step 5 — Mark delta spec as archived
After merging the delta, mark the delta spec as archived:
\`update_artifact(name="<delta-spec-name>", status="archived", metadata={"synced_at": "<ISO timestamp>", "merged_into": "<main-spec-name>"}, project_slug="${slug}")\`

## Step 6 — Record the sync
\`record_trace(action="sync", result_summary="Synced delta for capability: <capability> into main spec", project_slug="${slug}")\`
Tell the user which capabilities were updated.
`,
    },

    // ── <opsr:archive ───────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "archive",
      content: `${artifactHeader("/opsr:archive")}## Purpose
Finalize a completed change by archiving all its artifacts.
Runs verification checks, syncs delta specs to main specs, then archives everything.

## Input
$ARGUMENTS = change name. If not provided, list active changes and ask.

## Step 1 — Get full status of the change
\`list_artifacts(type="proposal", project_slug="${slug}")\`
Select the change to archive (or use $ARGUMENTS).
\`get_relationships(name="<change-name>-proposal", project_slug="${slug}")\`
Get all linked artifacts (specs, design, tasks).

## Step 2 — Validate artifact completion
Check each artifact status:
\`list_artifacts(type="task", status="draft", project_slug="${slug}")\`
If pending tasks exist → warn the user and ask for confirmation to archive anyway.

## Step 3 — Validate task completion
Count draft vs archived tasks. If any draft tasks remain → warn and confirm.

## Step 4 — Check for delta specs that need syncing
\`list_artifacts(type="spec", project_slug="${slug}")\`
Filter for specs where metadata.change_name = "<change-name>" AND metadata.is_delta = true.

If delta specs exist:
- Show which capabilities have deltas
- Ask: "Sync delta specs to main specs now? (recommended)"
- If yes → execute <opsr:sync logic for each delta spec
- If no → archive without syncing

${harnessChecklistStep("on_archive", "Archiving change artifacts")}
## Step 5 — Archive all change artifacts
For each artifact in this change (proposal, all specs, design, all tasks):
\`update_artifact(name="<artifact-name>", status="archived", metadata={"archived_at": "<ISO timestamp>", "change_name": "<change-name>"}, project_slug="${slug}")\`

## Step 6 — Record and show summary
\`record_trace(action="archive", result_summary="Archived change: <change-name> (<N> artifacts)", project_slug="${slug}")\`
Show summary:
- Artifacts archived: list
- Specs synced: list (if any)
- "Change <change-name> is complete."
`,
    },

    // ── <opsr:explore ───────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "explore",
      content: `${artifactHeader("/opsr:explore")}## Purpose
Think through a problem, idea, or question WITHOUT implementing anything.
Explore creates understanding before committing to a proposal.
You may create OpenSddRag artifacts to capture insights, but NEVER write application code.

## Input
$ARGUMENTS = topic, question, or idea to explore.

## Stance
You are in THINKING MODE. Your role is to:
- Ask clarifying questions
- Surface multiple options with trade-offs
- Investigate the codebase (read-only)
- Create ASCII diagrams to illustrate ideas
- Challenge assumptions
- Reference existing specs for context

You MUST NOT:
- Write application code
- Create implementation files
- Make changes to the codebase

## Step 1 — Check for existing related work
\`search_semantic(query="$ARGUMENTS", project_slug="${slug}", limit=5)\`
\`recall_episodes(query="$ARGUMENTS", project_slug="${slug}", limit=3)\`
Share any existing specs or past decisions that are relevant.

## Step 2 — Investigate and think
- Read relevant codebase files (read-only)
- Identify constraints and dependencies
- Surface at least 2 different approaches
- For each approach, list trade-offs

## Step 3 — Capture insights (if user asks)
If the user wants to capture a finding or decision, create an artifact:
\`create_artifact(name="explore-<topic>-<date>", type="proposal", content="<exploration notes, options, trade-offs>", metadata={"explore": true}, project_slug="${slug}")\`

## Step 4 — Transition when ready
When the user has enough insight to decide:
- Summarize key findings and recommendation
- Ask: "Ready to create a formal proposal? Run \`<opsr:propose <name>\`"
`,
    },

    // ── <opsr:continue ─────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "continue",
      content: `${artifactHeader("/opsr:continue")}## Purpose
Create the NEXT single artifact in the dependency chain for a change.
Unlike /opsr:flow which creates all artifacts, this creates ONE artifact and stops.
Dependency order: proposal → specs → design → tasks.

## Input
$ARGUMENTS = change name.

## Step 1 — Get current status from database
\`list_artifacts(type="proposal", project_slug="${slug}")\`
Identify the change to continue.
\`get_relationships(name="<change-name>-proposal", project_slug="${slug}")\`
Get all existing artifacts for this change.

## Step 2 — Find the next artifact to create
Check which artifacts exist and which are missing, in dependency order:
1. proposal → if missing, stop (must run <opsr:propose first)
2. specs → if any capability has no spec → create ONE spec and stop
3. design → if missing and all specs exist → create design and stop
4. tasks → if missing and design exists → create tasks and stop

If all artifacts exist → tell the user "All planning artifacts complete. Run /apply."

## Step 3 — Create the NEXT artifact only
Follow the logic from the corresponding command:
- For spec: follow /opsr:spec steps for ONE capability
- For design: follow /opsr:design steps
- For tasks: follow <opsr:tasks steps

## Step 4 — Show progress
After creating the artifact:
- Show what was created
- Show what is now unlocked (next in dependency chain)
- Suggest: "Run \`<opsr:continue <change-name>\` to create the next artifact."
`,
    },

    // ── <opsr:status ────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "status",
      content: `${artifactHeader("/opsr:status")}## Purpose
Show the current state of all in-progress changes for this project.
Reads from the MCP server — no local files involved.

## Input
$ARGUMENTS = optional change name to show details for one change. If not provided, show all.

## Step 1 — Load working context
\`get_working_context(project_slug="${slug}")\`

## Step 2 — List all artifacts by type and status
\`list_artifacts(type="proposal", status="draft", project_slug="${slug}")\`
\`list_artifacts(type="proposal", status="active", project_slug="${slug}")\`
\`list_artifacts(type="spec", status="draft", project_slug="${slug}")\`
\`list_artifacts(type="design", status="draft", project_slug="${slug}")\`
\`list_artifacts(type="task", status="draft", project_slug="${slug}")\`
\`list_artifacts(type="task", status="active", project_slug="${slug}")\`

## Step 3 — Recall recent activity
\`recall_episodes(query="recent actions in this project", project_slug="${slug}", limit=5)\`

## Step 4 — Present structured status

For each active change, show:
\`\`\`
## Change: <change-name>
| Artifact | Status |
|----------|--------|
| Proposal | ✓ done |
| Specs    | ✓ 2/2  |
| Design   | ✓ done |
| Tasks    | 3/5 done |

Current task: <task-name>
Next step: <opsr:apply <change-name>
\`\`\`

Then show:
- Recent activity (last 5 actions from episodic memory)
- Suggested next command based on current state
`,
    },

    // ── /opsr:flow ──────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "flow",
      content: `${artifactHeader("/opsr:flow")}## Purpose
Run the complete SDD flow end-to-end in a single session.
Planning artifacts (proposal, specs, design, tasks) are saved to the database via MCP tools.
Implementation code (Phase 5) is written locally using standard file tools (Edit, Write, Bash).

## Input
$ARGUMENTS = feature description or change name.

## PHASE 1 — Propose
Follow <opsr:propose steps:
1. \`search_semantic(query="$ARGUMENTS", project_slug="${slug}")\` — check for duplicates
2. Compose proposal content (Why / What Changes / Capabilities / Impact)
3. \`create_artifact(name="<change-name>-proposal", type="proposal", content="...", project_slug="${slug}")\`

## PHASE 2 — Spec
Follow /opsr:spec steps for each capability in the proposal:
4. For each capability: compose spec (Purpose / Requirements with SHALL / Scenarios with WHEN-THAN)
5. \`create_artifact(name="<change-name>-<capability>-spec", type="spec", content="...", project_slug="${slug}")\`
6. \`link_artifacts(source_name="<spec>", target_name="<proposal>", relationship_type="implements", project_slug="${slug}")\`
7. \`validate_artifact(name="<spec>", project_slug="${slug}")\` — fix errors before continuing

## PHASE 3 — Design
Follow /opsr:design steps:
8. Read all specs just created
9. Compose design (Context / Goals / Decisions / Architecture / Risks / Migration)
10. \`create_artifact(name="<change-name>-design", type="design", content="...", project_slug="${slug}")\`
11. \`link_artifacts(source_name="<design>", target_name="<proposal>", relationship_type="depends_on", project_slug="${slug}")\`

## PHASE 4 — Tasks
Follow <opsr:tasks steps:
12. Read proposal, all specs, and design from database
13. For each task: \`create_artifact(name="<change-name>-task-<N>", type="task", content="...", project_slug="${slug}")\`
14. \`link_artifacts(source_name="<task>", target_name="<spec>", relationship_type="implements", project_slug="${slug}")\`

## PHASE 5 — Apply (repeat for each task in order)
> **Implementation phase:** Code changes are written to local files using Edit, Write, and Bash. MCP tools are used only to read planning artifacts and record traces.

Follow <opsr:apply steps:
15. Read ALL planning artifacts as context (proposal + specs + design)
16. \`update_artifact(name="<task>", status="active", project_slug="${slug}")\`
17. Implement the task against its acceptance criteria (write code locally using Edit/Write/Bash)
18. \`update_artifact(name="<task>", status="archived", project_slug="${slug}")\`
19. \`record_trace(action="apply_task", result_summary="Completed: <task>", project_slug="${slug}")\`

## PHASE 6 — Archive
Follow <opsr:archive steps:
20. Sync delta specs if any
21. \`update_artifact(name="<all artifacts>", status="archived", project_slug="${slug}")\`
22. \`record_trace(action="complete_flow", result_summary="Completed: $ARGUMENTS", project_slug="${slug}")\`
`,
    },

    // ── <opsr:search ────────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "search",
      content: `${artifactHeader("/opsr:search")}## Purpose
Search the SDD knowledge base using semantic similarity (pgvector).
Use this BEFORE starting any new work to find existing specs, decisions, and past implementations.

## Input
$ARGUMENTS = natural language search query.

## Step 1 — Search this project
\`search_semantic(query="$ARGUMENTS", project_slug="${slug}", limit=5)\`

## Step 2 — If no relevant results, search all projects
\`search_semantic(query="$ARGUMENTS", project_slug="*", limit=5)\`

## Step 3 — Recall past actions related to the query
\`recall_episodes(query="$ARGUMENTS", project_slug="${slug}", limit=3)\`

## Step 4 — Present results clearly
For each result: name, type, status, and a content excerpt (first 200 chars).
Group by: this project / other projects / past actions.

## Step 5 — Offer to read the full artifact
\`read_artifact(name="<artifact-name>", project_slug="${slug}")\`
`,
    },

    // ── <opsr:harness ───────────────────────────────────────────────────────────
    {
      folder: "opsr",
      name: "harness",
      content: `${harnessHeader("/opsr:harness")}## Purpose
Manage project harness rules: add new rules, list existing rules, and disable rules that are no longer needed.
Harness rules are persistent behavioral constraints injected into every agent session via \`get_working_context\` (for \`trigger="always"\` rules) and surfaced as phase-gate checklists via \`get_harness_checklist\`.

## Input
$ARGUMENTS = one of:
- \`add\` — followed by rule fields or a natural-language description
- \`list\` — show all rules for this project
- \`disable <rule-name>\` — soft-delete a rule by name

If $ARGUMENTS is empty, show the current rules list and ask what the user wants to do.

## Supported rule fields

| Field | Values |
|-------|--------|
| \`name\`        | kebab-case slug, unique per project |
| \`trigger\`     | \`always\` (every session) / \`on_apply\` / \`on_verify\` / \`on_archive\` / \`on_spec\` |
| \`category\`    | \`architecture\` / \`naming\` / \`forbidden\` / \`doc-sync\` / \`verification\` |
| \`severity\`    | \`error\` (MUST satisfy) / \`warning\` (SHOULD satisfy) / \`info\` (advisory) |
| \`instruction\` | free-text rule the agent must follow |
| \`metadata\`    | optional JSON |
| \`enabled\`     | \`true\` (default) / \`false\` (soft-delete) |

## Step 1 — Parse the operation

If $ARGUMENTS starts with \`add\`:
  → Go to **Step 2A — Add**

If $ARGUMENTS starts with \`list\`:
  → Go to **Step 2B — List**

If $ARGUMENTS starts with \`disable <name>\`:
  → Go to **Step 2C — Disable**

If $ARGUMENTS is empty:
  → Call \`list_rules(project_slug="${slug}")\` and show the current state. Ask the user what they want to do.

## Step 2A — Add a rule

If the user provided explicit fields after \`add\` (e.g. \`add name=repo-pattern trigger=always category=architecture severity=error instruction="..."\`), use them as-is.

Otherwise, ask the user for each field. **You can infer sensible defaults from natural language:**
- "always update CHANGELOG when applying" → trigger=\`on_apply\`, category=\`doc-sync\`, severity=\`warning\`
- "never do X" → trigger=\`always\`, category=\`forbidden\`, severity=\`error\`
- "use Y pattern" → trigger=\`always\`, category=\`architecture\`, severity=\`warning\`

**Show the inferred values and ask for confirmation** before calling \`add_rule\`.

Then call:

\`\`\`
add_rule(
  name:        "<kebab-case>",
  trigger:     "<always|on_apply|on_verify|on_archive|on_spec>",
  category:    "<architecture|naming|forbidden|doc-sync|verification>",
  severity:    "<error|warning|info>",
  instruction: "<text>",
  project_slug:"${slug}",
  enabled:     true
)
\`\`\`

Confirm to the user:
"Rule '<name>' added. It will [be injected into every working context | be checked during /opsr:<trigger> when the phase completes]."

Then record the operation:
\`record_trace(action="add_rule", result_summary="Added harness rule: <name>", project_slug="${slug}")\`

## Step 2B — List rules

Call:

\`list_rules(project_slug="${slug}", enabled_only=true)\`

Present the results **grouped by trigger**, in this order:

\`\`\`
### Always (loaded at session start)
- [<category>:<severity>] <name> — <truncated instruction (max 80 chars)>

### On Apply (checked during /opsr:apply)
- ...

### On Verify (checked during /opsr:verify)
- ...

### On Archive (checked during /opsr:archive)
- ...

### On Spec (checked during /opsr:spec)
- ...
\`\`\`

If the result list is empty, respond:
"No harness rules defined for this project. Run \`/opsr:harness add\` to create the first rule."

If rules exist in only some sections, show "(none)" for empty sections.

## Step 2C — Disable a rule

Extract the rule name from $ARGUMENTS (the token after \`disable\`).

Call:

\`add_rule(name: "<name>", enabled: false, project_slug: "${slug}")\`

(You don't need to pass the other fields — \`add_rule\` is an upsert keyed on \`(project_id, name)\` and will set the existing rule's \`enabled\` flag to \`false\`.)

Confirm:
"Rule '<name>' disabled. It will no longer appear in checklists or session context. Re-add with the same name to re-enable."

Then record:
\`record_trace(action="disable_rule", result_summary="Disabled harness rule: <name>", project_slug="${slug}")\`

## Notes

- The same \`add_rule\` MCP call is used for create, update, and soft-delete — it is idempotent on \`(project_id, name)\`.
- Disabled rules are preserved in the database and can be re-enabled by calling \`add_rule\` with the same \`name\` and \`enabled=true\`.
- Rules are project-scoped — they never leak across projects.
- The OpenCode equivalent of this command is the \`opensddrag-harness\` skill, which calls the same MCP tools.
`,
    },
  ];
}