export function getOpenCodeSkills(slug, _serverUrl) {
  const note = `> **project_slug for every call:** \`${slug}\`\n\n`;

  const fm = (name, description) => `---\nname: ${name}\ndescription: ${description}\n---\n\n`;

  return [
    {
      name: "opensddrag-propose",
      content: `${fm("opensddrag-propose", "Create a named change proposal — entry point for every feature or bugfix")}# OpenSddRag — Propose
${note}Creates a named **change** with a proposal artifact: Why, What Changes, Capabilities, Impact.
Entry point for every new feature or bugfix. No code is written here.
After this, /opsr:spec and /opsr:design become available.

**Run:** \`/opsr:propose <change-name or description>\`

**Creates:** \`<change-name>-proposal\` artifact in database.
**Unlocks:** /opsr:spec, /opsr:design
`,
    },
    {
      name: "opensddrag-spec",
      content: `${fm("opensddrag-spec", "Write capability specs with SHALL/MUST requirements and WHEN/THEN scenarios")}# OpenSddRag — Spec
${note}Creates spec artifacts for each capability listed in the proposal.
Uses SHALL/MUST language. Each requirement MUST have Scenarios with WHEN/THEN format.

**New capability** → full spec (Purpose + Requirements + Scenarios)
**Modified capability** → delta spec (ADDED / MODIFIED / REMOVED / RENAMED sections)

**Run:** \`/opsr:spec <change-name>\`

**Requires:** proposal artifact in database.
**Creates:** \`<change-name>-<capability>-spec\` artifact(s) in database.
**Unlocks:** /opsr:design (when all capabilities have specs)
`,
    },
    {
      name: "opensddrag-design",
      content: `${fm("opensddrag-design", "Document technical decisions, architecture, and trade-offs for a change")}# OpenSddRag — Design
${note}Creates a design document: Context, Goals, Decisions (with alternatives), Architecture, Risks, Migration.
Must read proposal and all specs from the database as context.

**Run:** \`/opsr:design <change-name>\`

**Requires:** proposal + specs in database.
**Creates:** \`<change-name>-design\` artifact in database.
**Unlocks:** /opsr:tasks
`,
    },
    {
      name: "opensddrag-tasks",
      content: `${fm("opensddrag-tasks", "Break a design into atomic, verifiable implementation tasks")}# OpenSddRag — Tasks
${note}Decomposes specs + design into atomic task artifacts, each < 4 hours.
Each task has: Goal, Acceptance criteria (referencing REQ-NNN), Dependencies.
Tasks are individual database artifacts — NOT a single markdown file.

**Run:** \`/opsr:tasks <change-name>\`

**Requires:** proposal + specs + design in database.
**Creates:** \`<change-name>-task-<N>\` artifacts in database.
**Unlocks:** /opsr:apply
`,
    },
    {
      name: "opensddrag-apply",
      content: `${fm("opensddrag-apply", "Implement the next pending task against spec acceptance criteria")}# OpenSddRag — Apply
${note}Implements tasks one at a time, reading ALL planning artifacts (proposal + specs + design) as context.
Marks tasks active → archived in the database after implementation.
Must validate each task against spec acceptance criteria before marking done.

**Run:** \`/opsr:apply <change-name>\`

**Requires:** all planning artifacts + pending tasks in database.
**Updates:** task status in database (draft → active → archived).
**After all tasks:** run /opsr:verify then /opsr:archive.
`,
    },
    {
      name: "opensddrag-verify",
      content: `${fm("opensddrag-verify", "Validate implementation against spec requirements and design decisions")}# OpenSddRag — Verify
${note}Read-only validation of the implementation against spec requirements and design decisions.
Produces a report with CRITICAL / WARNING / SUGGESTION severity levels.

Checks:
- **Completeness**: all tasks done, all REQ-NNN implemented
- **Correctness**: all spec scenarios covered
- **Coherence**: implementation follows design decisions

**Run:** \`/opsr:verify <change-name>\`

**Requires:** all artifacts in database + implementation in codebase.
**Output:** verification report (no artifacts modified).
`,
    },
    {
      name: "opensddrag-sync",
      content: `${fm("opensddrag-sync", "Merge delta specs back into main capability specs")}# OpenSddRag — Sync
${note}Merges delta specs (ADDED/MODIFIED/REMOVED/RENAMED) into main specs stored in the database.
Called automatically during /opsr:archive when delta specs exist.

Delta operations:
- **ADDED** → append new requirement to main spec
- **MODIFIED** → apply partial updates (not wholesale replace)
- **REMOVED** → delete requirement + add Reason/Migration note
- **RENAMED** → rename requirement heading

**Run:** \`/opsr:sync <change-name>\`

**Requires:** delta specs + main specs in database.
**Updates:** main spec artifacts in database.
`,
    },
    {
      name: "opensddrag-archive",
      content: `${fm("opensddrag-archive", "Finalize a completed change by archiving all its artifacts")}# OpenSddRag — Archive
${note}Finalizes a completed change: validates, syncs delta specs, archives all artifacts.

Steps:
1. Validate artifact and task completion (warns if incomplete)
2. Sync delta specs to main specs (if any)
3. Mark all change artifacts as archived in database

**Run:** \`/opsr:archive <change-name>\`

**Requires:** all tasks completed (or user confirmation to archive anyway).
**Updates:** all change artifacts to status=archived in database.
`,
    },
    {
      name: "opensddrag-explore",
      content: `${fm("opensddrag-explore", "Investigate a problem or idea without writing any code")}# OpenSddRag — Explore
${note}Thinking mode — investigates ideas WITHOUT implementing any code.
Reads existing specs and codebase for context. Can create artifacts to capture insights.

Rules:
- NEVER write application code
- NEVER create implementation files
- MAY create/update OpenSddRag artifacts to capture decisions

Use when: thinking through options, investigating feasibility, comparing approaches.
Transition: when ready → /opsr:propose <name>

**Run:** \`/opsr:explore <topic or question>\`
`,
    },
    {
      name: "opensddrag-continue",
      content: `${fm("opensddrag-continue", "Create the next single artifact in the SDD dependency chain")}# OpenSddRag — Continue
${note}Creates the NEXT SINGLE artifact in the dependency chain and stops.
Unlike /opsr:flow, creates one artifact per invocation.

Dependency order: proposal → specs → design → tasks

Use when: stepping through the SDD flow one artifact at a time.

**Run:** \`/opsr:continue <change-name>\`
`,
    },
    {
      name: "opensddrag-status",
      content: `${fm("opensddrag-status", "Show current state of all in-progress changes")}# OpenSddRag — Status
${note}Shows current state of all in-progress changes: artifact completion, task progress, recent activity.

Reads from MCP server — no local files.

**Run:** \`/opsr:status\` or \`/opsr:status <change-name>\`
`,
    },
    {
      name: "opensddrag-flow",
      content: `${fm("opensddrag-flow", "Run the complete SDD flow end-to-end in one session")}# OpenSddRag — Flow
${note}Runs the complete SDD flow end-to-end: propose → spec → design → tasks → apply → archive.
ALL artifacts saved to database via MCP — no local files created.

Use when: implementing a feature from scratch in a single session.

**Run:** \`/opsr:flow <feature description>\`
`,
    },
    {
      name: "opensddrag-search",
      content: `${fm("opensddrag-search", "Semantic search over specs, tasks, and past agent actions")}# OpenSddRag — Search
${note}Semantic search over the SDD knowledge base using pgvector similarity.
Always run this BEFORE starting new work to find existing specs and decisions.

Searches: this project first, then all projects if no results.
Also recalls past agent actions (episodic memory).

**Run:** \`/opsr:search <natural language query>\`
`,
    },
  ];
}

export function getSkills(slug, serverUrl) {
  const note = `> **MCP server:** \`opensddrag\` (${serverUrl}) | **project_slug:** \`${slug}\`
> **Available tools:** \`create_artifact\`, \`read_artifact\`, \`list_artifacts\`, \`update_artifact\`, \`validate_artifact\`, \`link_artifacts\`, \`get_relationships\`, \`search_semantic\`, \`recall_episodes\`, \`get_working_context\`, \`update_working_context\`, \`record_trace\`
> If these tools are not in your active tool list, the \`opensddrag\` MCP server is not connected — STOP and inform the user.\n\n`;

  const fm = (name, description) => `---\nname: ${name}\ndescription: ${description}\n---\n\n`;

  return [
    {
      name: "opensddrag-propose",
      content: `${fm("opensddrag-propose", "Create a named change proposal — entry point for every feature or bugfix")}# OpenSddRag — Propose
${note}Creates a named **change** with a proposal artifact: Why, What Changes, Capabilities, Impact.
Entry point for every new feature or bugfix. No code is written here.
After this, /opsr:spec and /opsr:design become available.

**Run:** \`/opsr:propose <change-name or description>\`

**Creates:** \`<change-name>-proposal\` artifact in database.
**Unlocks:** /opsr:spec, /opsr:design
`,
    },
    {
      name: "opensddrag-spec",
      content: `${fm("opensddrag-spec", "Write capability specs with SHALL/MUST requirements and WHEN/THEN scenarios")}# OpenSddRag — Spec
${note}Creates spec artifacts for each capability listed in the proposal.
Uses SHALL/MUST language. Each requirement MUST have Scenarios with WHEN/THEN format.

**New capability** → full spec (Purpose + Requirements + Scenarios)
**Modified capability** → delta spec (ADDED / MODIFIED / REMOVED / RENAMED sections)

**Run:** \`/opsr:spec <change-name>\`

**Requires:** proposal artifact in database.
**Creates:** \`<change-name>-<capability>-spec\` artifact(s) in database.
**Unlocks:** /opsr:design (when all capabilities have specs)
`,
    },
    {
      name: "opensddrag-design",
      content: `${fm("opensddrag-design", "Document technical decisions, architecture, and trade-offs for a change")}# OpenSddRag — Design
${note}Creates a design document: Context, Goals, Decisions (with alternatives), Architecture, Risks, Migration.
Must read proposal and all specs from the database as context.

**Run:** \`/opsr:design <change-name>\`

**Requires:** proposal + specs in database.
**Creates:** \`<change-name>-design\` artifact in database.
**Unlocks:** /opsr:tasks
`,
    },
    {
      name: "opensddrag-tasks",
      content: `${fm("opensddrag-tasks", "Break a design into atomic, verifiable implementation tasks")}# OpenSddRag — Tasks
${note}Decomposes specs + design into atomic task artifacts, each < 4 hours.
Each task has: Goal, Acceptance criteria (referencing REQ-NNN), Dependencies.
Tasks are individual database artifacts — NOT a single markdown file.

**Run:** \`/opsr:tasks <change-name>\`

**Requires:** proposal + specs + design in database.
**Creates:** \`<change-name>-task-<N>\` artifacts in database.
**Unlocks:** /opsr:apply
`,
    },
    {
      name: "opensddrag-apply",
      content: `${fm("opensddrag-apply", "Implement the next pending task against spec acceptance criteria")}# OpenSddRag — Apply
${note}Implements tasks one at a time, reading ALL planning artifacts (proposal + specs + design) as context.
Marks tasks active → archived in the database after implementation.
Must validate each task against spec acceptance criteria before marking done.

**Run:** \`/opsr:apply <change-name>\`

**Requires:** all planning artifacts + pending tasks in database.
**Updates:** task status in database (draft → active → archived).
**After all tasks:** run /opsr:verify then /opsr:archive.
`,
    },
    {
      name: "opensddrag-verify",
      content: `${fm("opensddrag-verify", "Validate implementation against spec requirements and design decisions")}# OpenSddRag — Verify
${note}Read-only validation of the implementation against spec requirements and design decisions.
Produces a report with CRITICAL / WARNING / SUGGESTION severity levels.

Checks:
- **Completeness**: all tasks done, all REQ-NNN implemented
- **Correctness**: all spec scenarios covered
- **Coherence**: implementation follows design decisions

**Run:** \`/opsr:verify <change-name>\`

**Requires:** all artifacts in database + implementation in codebase.
**Output:** verification report (no artifacts modified).
`,
    },
    {
      name: "opensddrag-sync",
      content: `${fm("opensddrag-sync", "Merge delta specs back into main capability specs")}# OpenSddRag — Sync
${note}Merges delta specs (ADDED/MODIFIED/REMOVED/RENAMED) into main specs stored in the database.
Called automatically during /opsr:archive when delta specs exist.

Delta operations:
- **ADDED** → append new requirement to main spec
- **MODIFIED** → apply partial updates (not wholesale replace)
- **REMOVED** → delete requirement + add Reason/Migration note
- **RENAMED** → rename requirement heading

**Run:** \`/opsr:sync <change-name>\`

**Requires:** delta specs + main specs in database.
**Updates:** main spec artifacts in database.
`,
    },
    {
      name: "opensddrag-archive",
      content: `${fm("opensddrag-archive", "Finalize a completed change by archiving all its artifacts")}# OpenSddRag — Archive
${note}Finalizes a completed change: validates, syncs delta specs, archives all artifacts.

Steps:
1. Validate artifact and task completion (warns if incomplete)
2. Sync delta specs to main specs (if any)
3. Mark all change artifacts as archived in database

**Run:** \`/opsr:archive <change-name>\`

**Requires:** all tasks completed (or user confirmation to archive anyway).
**Updates:** all change artifacts to status=archived in database.
`,
    },
    {
      name: "opensddrag-explore",
      content: `${fm("opensddrag-explore", "Investigate a problem or idea without writing any code")}# OpenSddRag — Explore
${note}Thinking mode — investigates ideas WITHOUT implementing any code.
Reads existing specs and codebase for context. Can create artifacts to capture insights.

Rules:
- NEVER write application code
- NEVER create implementation files
- MAY create/update OpenSddRag artifacts to capture decisions

Use when: thinking through options, investigating feasibility, comparing approaches.
Transition: when ready → /opsr:propose <name>

**Run:** \`/opsr:explore <topic or question>\`
`,
    },
    {
      name: "opensddrag-continue",
      content: `${fm("opensddrag-continue", "Create the next single artifact in the SDD dependency chain")}# OpenSddRag — Continue
${note}Creates the NEXT SINGLE artifact in the dependency chain and stops.
Unlike /opsr:flow, creates one artifact per invocation.

Dependency order: proposal → specs → design → tasks

Use when: stepping through the SDD flow one artifact at a time.

**Run:** \`/opsr:continue <change-name>\`
`,
    },
    {
      name: "opensddrag-status",
      content: `${fm("opensddrag-status", "Show current state of all in-progress changes")}# OpenSddRag — Status
${note}Shows current state of all in-progress changes: artifact completion, task progress, recent activity.

Reads from MCP server — no local files.

**Run:** \`/opsr:status\` or \`/opsr:status <change-name>\`
`,
    },
    {
      name: "opensddrag-flow",
      content: `${fm("opensddrag-flow", "Run the complete SDD flow end-to-end in one session")}# OpenSddRag — Flow
${note}Runs the complete SDD flow end-to-end: propose → spec → design → tasks → apply → archive.
ALL artifacts saved to database via MCP — no local files created.

Use when: implementing a feature from scratch in a single session.

**Run:** \`/opsr:flow <feature description>\`
`,
    },
    {
      name: "opensddrag-search",
      content: `${fm("opensddrag-search", "Semantic search over specs, tasks, and past agent actions")}# OpenSddRag — Search
${note}Semantic search over the SDD knowledge base using pgvector similarity.
Always run this BEFORE starting new work to find existing specs and decisions.

Searches: this project first, then all projects if no results.
Also recalls past agent actions (episodic memory).

**Run:** \`/opsr:search <natural language query>\`
`,
    },
  ];
}
