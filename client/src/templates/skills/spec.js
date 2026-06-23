import { harnessChecklistBlock } from "./_shared.js";

export const specSkill = {
  name: "opensddrag-spec",
  description:
    "Write capability specs with SHALL/MUST requirements and WHEN/THEN scenarios",
  body: (slug, note) => `# OpenSddRag — Spec
${note}## When to use
After a proposal exists, to formalize each capability into a spec artifact with SHALL/MUST
requirements and WHEN/THEN scenarios. Each capability in the proposal gets its own spec.

## Inputs
$ARGUMENTS = change name. If not provided, list proposals and ask which one.

## Workflow

### Step 1 — Read the proposal
\`list_artifacts(type="proposal", project_slug="${slug}")\`
\`read_artifact(name="<change-name>-proposal", project_slug="${slug}")\`

### Step 2 — Identify capabilities
Parse "## Capabilities". Every capability in "New Capabilities" and "Modified Capabilities" needs a spec.
- **New capability** → full spec (Purpose + Requirements + Scenarios).
- **Modified capability** → check for an existing main spec: \`search_semantic(query="<capability> spec", project_slug="${slug}", limit=3)\`.
  - If a main spec exists → create a DELTA spec (ADDED/MODIFIED/REMOVED/RENAMED).
  - If no main spec → create BOTH the main spec (is_delta=false) and the delta spec (is_delta=true).

### Step 3 — Write spec content for each capability

Full spec structure (new capabilities):
\`\`\`markdown
# <capability> Specification

## Purpose
[High-level description]

## Requirements

### Requirement: REQ-001 <Name>
[Description using SHALL/MUST language]

#### Scenario: <Happy path>
- **WHEN** [condition]
- **THEN** [expected outcome]

#### Scenario: <Edge case>
- **WHEN** [edge condition]
- **THEN** [expected outcome]
\`\`\`

Delta spec structure (modified capabilities):
\`\`\`markdown
# <capability> Specification — Delta

## ADDED Requirements
### Requirement: <New name>
[Full requirement with scenarios]

## MODIFIED Requirements
### Requirement: <Existing name>
[Full updated text with all scenarios]

## REMOVED Requirements
### Requirement: <Removed name>
**Reason:** [why] · **Migration:** [how consumers migrate]

## RENAMED Requirements
- FROM: \`### Requirement: Old Name\`
- TO: \`### Requirement: New Name\`
\`\`\`

### Step 4 — Save each spec
\`create_artifact(name="<change-name>-<capability>-spec", type="spec", content="<full spec markdown>", metadata={"change_name": "<change-name>", "capability": "<capability>", "is_delta": true|false}, project_slug="${slug}")\`

### Step 5 — Link each spec to the proposal
\`link_artifacts(source_name="<spec>", target_name="<change-name>-proposal", relationship_type="implements", project_slug="${slug}")\`

### Step 6 — Validate each spec
\`validate_artifact(name="<spec>", project_slug="${slug}")\` — fix any validation errors before continuing.

${harnessChecklistBlock(slug, "on_spec", "Saving specs to the database")}
### Step 7 — Record the action
\`record_trace(action="spec", result_summary="Created specs for: <capability-list>", project_slug="${slug}")\`

## Output
- One spec artifact per capability (full and/or delta) linked to the proposal.
- **Unlocks:** /opsr:design once all capabilities have specs.

## Important rules
- Every requirement MUST have at least one WHEN/THEN scenario.
- Delta specs MUST carry metadata.is_delta=true so /opsr:sync can merge them later.
- Run the harness checklist (on_spec) before declaring specs done.
`,
};
