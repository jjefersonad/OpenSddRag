export const designSkill = {
  name: "opensddrag-design",
  description:
    "Document technical decisions, architecture, and trade-offs for a change",
  body: (slug, note) => `# OpenSddRag — Design
${note}## When to use
After the specs exist, to capture the technical decisions, architecture, trade-offs, and open
questions for a change. The design is grounded in the proposal and spec artifacts already saved.

## Inputs
$ARGUMENTS = change name.

## Workflow

### Step 1 — Read proposal and all specs
\`read_artifact(name="<change-name>-proposal", project_slug="${slug}")\`
\`list_artifacts(type="spec", project_slug="${slug}")\`
\`get_relationships(name="<change-name>-proposal", project_slug="${slug}")\`
Read each spec linked to this change.

### Step 2 — Search for related prior designs
\`search_semantic(query="<change topic> design decisions", project_slug="${slug}", limit=3)\`
Use findings as context — do not duplicate prior work.

### Step 3 — Write the design content
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

## Architecture
[Components, data flow, integration points — ASCII diagrams if helpful]

## Risks / Trade-offs
| Risk | Mitigation |
|------|------------|
| [Risk] | [Mitigation] |

## Migration Plan
[Deployment steps, backward compatibility, rollback plan]

## Open Questions
- [ ] [Question that still needs resolution]
\`\`\`

### Step 4 — Save the design
\`create_artifact(name="<change-name>-design", type="design", content="<full design markdown>", metadata={"change_name": "<change-name>"}, project_slug="${slug}")\`
If a draft design skeleton already exists, use \`update_artifact\` instead of creating a duplicate.

### Step 5 — Link the design to the proposal
\`link_artifacts(source_name="<change-name>-design", target_name="<change-name>-proposal", relationship_type="depends_on", project_slug="${slug}")\`

### Step 6 — Record and show next steps
\`record_trace(action="design", result_summary="Created design: <change-name>-design", project_slug="${slug}")\`
Tell the user: "Design saved. Run /opsr:tasks <change-name> to decompose into tasks."

## Output
- A \`<change-name>-design\` artifact linked to the proposal.
- **Unlocks:** /opsr:tasks.

## Important rules
- Every Decision MUST list the chosen approach AND the alternatives considered with reasons.
- DO NOT write application code — this phase is design only.
- If a design already exists, amend it (update_artifact) rather than creating a second one.
`,
};
