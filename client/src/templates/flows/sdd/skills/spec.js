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

### Step 7 — Scenario confirmation gate (then create scenario-level test artifacts)
For every spec created/updated in Step 4, parse the markdown and extract every \`#### Scenario: <Name>\` block, grouped by its parent \`### Requirement: REQ-NNN <Name>\`. For each spec, list the cap/spec slug and the count of scenarios found, then present the aggregated scenarios to the user grouped by REQ, in this format:

\`\`\`
Scenarios to confirm for change '<change-name>':

Spec: <change-name>-<capability>-spec
  REQ-001 <Requirement name>
    1. <Scenario name>
       WHEN: <when clause>
       THEN: <then clause>
    2. <Scenario name>
       WHEN: <when clause>
       THEN: <then clause>
  REQ-002 <Requirement name>
    1. ...
\`\`\`

Then \`STOP\` and ask the user:

\`\`\`
Confirm the scenarios above (yes / adjust / abort):
- yes    → create one \`test\` artifact per confirmed scenario (level="scenario",
            test_status="pending") linked to its spec via \`implements\`, then
            continue to Step 8.
- adjust → tell me which spec + which scenario to change; I'll call
            \`update_artifact\`, re-validate, and re-present the scenarios.
- abort  → stop /opsr:spec here; nothing is created beyond what Step 4 already
            persisted.
\`\`\`

**Adjustment flow**: if the user picks "adjust", do NOT create any \`test\` artifact yet. Identify the affected spec, apply the change via \`update_artifact(name="<spec>", content="<updated markdown>", project_slug="${slug}")\`, re-run \`validate_artifact\` on it, and re-render the scenario list for that spec before re-asking. Loop until the user replies "yes" or "abort".

**Confirmation flow**: on "yes", for each scenario, call:

\`\`\`
create_artifact(
  name="<change-name>-<capability>-<requirement-id>-scenario-<n>",
  type="test",
  content="<verbatim scenario markdown block, from '#### Scenario:' through its WHEN/THEN lines>",
  metadata={
    "change_name": "<change-name>",
    "capability": "<capability>",
    "level": "scenario",
    "requirement_id": "REQ-NNN",
    "scenario_name": "<Scenario name>",
    "test_status": "pending",
    "is_delta": <true|false, copied from the parent spec>,
  },
  project_slug="${slug}"
)
\`\`\`

then link it to the parent spec:

\`link_artifacts(source_name="<change-name>-<capability>-<requirement-id>-scenario-<n>", target_name="<change-name>-<capability>-spec", relationship_type="implements", project_slug="${slug}")\`

Scenario-level test artifacts exist to make every WHEN/THEN individually addressable and queryable — they are the navigable handles used by apply (to confirm coverage) and verify (to confirm passing test_status before archive), per unified-test-artifact-type REQ-001/REQ-002 and sdd-workflow-lifecycle REQ-010. They MUST be created before Step 8 (the harness checklist) runs, so on_spec rules see a consistent set of linked scenario tests per spec.

${harnessChecklistBlock(slug, "on_spec", "Saving specs to the database")}
### Step 9 — Record the action
\`record_trace(action="spec", result_summary="Created specs for: <capability-list> with <N> scenario test artifacts", project_slug="${slug}")\`

## Output
- One spec artifact per capability (full and/or delta) linked to the proposal.
- One \`test\` artifact (type="test", level="scenario", test_status="pending") per confirmed scenario, linked to its spec via \`implements\`.
- **Unlocks:** /opsr:design once all capabilities have specs AND every confirmed scenario has a linked \`test\` artifact.

## Important rules
- Every requirement MUST have at least one WHEN/THEN scenario.
- Delta specs MUST carry metadata.is_delta=true so /opsr:sync can merge them later.
- Step 7 (scenario confirmation gate) MUST run BEFORE Step 8 (harness checklist) and BEFORE Step 9 (record_trace) — do not skip the user confirmation, even when scenarios look obvious.
- On "adjust", the affected spec is updated via \`update_artifact\` and re-validated before re-presenting; do not create \`test\` artifacts for scenarios the user has not yet confirmed.
- On "abort", do not create any \`test\` artifact; the spec remains in the database as created in Step 4 but the change is not considered ready for design.
- Run the harness checklist (on_spec) before declaring specs done.
`,
};
