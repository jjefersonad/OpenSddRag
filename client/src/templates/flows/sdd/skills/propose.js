export const proposeSkill = {
  name: "opensddrag-propose",
  description:
    "Create a named change proposal — entry point for every feature or bugfix",
  body: (slug, note) => `# OpenSddRag — Propose
${note}## When to use
Run this as the entry point for every new feature or bugfix, before any code is written.
It creates a named **change** with a proposal artifact defining WHY, WHAT changes, WHICH
capabilities are affected, and the IMPACT. After it, /opsr:spec and /opsr:design unlock.

## Inputs
$ARGUMENTS = change name (kebab-case) or a plain description. If a plain description, derive a kebab-case name.

## Workflow

### Step 1 — Derive the change name
If $ARGUMENTS is a plain description (contains spaces), convert it to kebab-case.
Example: "add user authentication" → "add-user-authentication".

### Step 2 — Search for existing work (avoid duplication)
\`search_semantic(query="$ARGUMENTS", project_slug="${slug}", limit=5)\`
If relevant artifacts are found, show them and ask the user to confirm this is genuinely new work.

### Step 3 — Write the proposal content
Compose this structure — do NOT skip any section:

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

### Step 4 — Save the proposal
\`create_artifact(name="<change-name>-proposal", type="proposal", content="<full proposal markdown>", metadata={"change_name": "<change-name>", "status_phase": "planning"}, project_slug="${slug}")\`
Note the returned artifact ID.

### Step 5 — Create spec drafts for each capability
Parse "## Capabilities". For each capability in "New Capabilities" or "Modified Capabilities":
1. Check if a spec already exists: \`read_artifact(name="<change-name>-<capability>-spec", project_slug="${slug}")\`. If it exists and is non-empty, skip.
2. Otherwise create a draft spec scaffold:
\`create_artifact(name="<change-name>-<capability>-spec", type="spec", status="draft", content="# <capability> Specification\\n\\n## Purpose\\n[TODO]\\n\\n## Requirements\\n\\n### Requirement: REQ-001\\n[TODO SHALL/MUST]\\n\\n#### Scenario: <Name>\\n- **WHEN** [condition]\\n- **THEN** [outcome]", metadata={"change_name": "<change-name>", "capability": "<capability>", "is_delta": true}, project_slug="${slug}")\`

### Step 6 — Create a design skeleton
\`create_artifact(name="<change-name>-design", type="design", status="draft", content="# Design: <change-name>\\n\\n## Context\\n[TODO]\\n\\n## Goals / Non-Goals\\n\\n## Decisions\\n\\n## Architecture\\n\\n## Risks / Trade-offs\\n\\n## Open Questions", metadata={"change_name": "<change-name>"}, project_slug="${slug}")\`

### Step 7 — Record the action
\`record_trace(action="propose", result_summary="Created proposal: <change-name>-proposal", project_slug="${slug}")\`

## Output
- A \`<change-name>-proposal\` artifact (plus draft spec/design scaffolds) in the database.
- **Unlocks:** /opsr:spec, /opsr:design, or /opsr:flow to continue automatically.

## Important rules
- NEVER write application code in this phase.
- DO NOT create local markdown files — all artifacts live in the database.
- If $ARGUMENTS is empty, ask the user for a change name or description before proceeding.
`,
};
