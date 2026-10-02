export const flowSkill = {
  name: "opensddrag-flow",
  description: "Run the complete SDD flow end-to-end in one session",
  body: (slug, note) => `# OpenSddRag — Flow
${note}## When to use
To run the complete SDD flow end-to-end in a single session: propose → spec → design → tasks →
apply → archive. Planning artifacts are saved to the database; implementation code is written locally.

This skill is a thin **orchestrator**: each phase delegates to the matching skill, which is the
single source of truth for that phase's workflow. Do NOT duplicate those steps here.

## Inputs
$ARGUMENTS = feature description or change name.

## Workflow

### Phase 1 — Propose
Load the \`opensddrag-propose\` skill and follow it: search for duplicates, compose the proposal
(Why / What Changes / Capabilities / Impact), and save the \`<change-name>-proposal\` artifact.

### Phase 2 — Spec
Load the \`opensddrag-spec\` skill and follow it for each capability in the proposal: compose the
spec (Purpose / Requirements with SHALL / Scenarios with WHEN-THEN), save it, link it to the
proposal, and validate it. Fix validation errors before continuing.

### Phase 3 — Design
Load the \`opensddrag-design\` skill and follow it: read all specs, compose the design
(Context / Goals / Decisions / Architecture / Risks / Migration), save it, and link it to the proposal.

### Phase 4 — Tasks
Load the \`opensddrag-tasks\` skill and follow it: read proposal + specs + design, create one task
artifact per unit of work, link each to its spec(s), and update the working context.

### Phase 5 — Apply (repeat for each task in order)
Load the \`opensddrag-apply\` skill and follow it for each task: read all planning artifacts, mark
the task active, implement it locally (Edit/Write/Bash), run the on_apply harness checklist, then
mark it archived and record a trace. Repeat until no draft tasks remain.

### Phase 6 — Archive
Load the \`opensddrag-archive\` skill and follow it: sync any delta specs, run the on_archive
harness checklist, archive all change artifacts, and record the completion trace.

## Resuming a partially-complete flow
Flow is idempotent at the phase level. Before each phase, check what already exists
(\`get_relationships(name="<change-name>-proposal", project_slug="${slug}")\`) and skip phases whose
artifacts are already present:
- Proposal exists → skip Phase 1.
- All capabilities specced → skip Phase 2.
- Design exists → skip Phase 3.
- Tasks exist → skip Phase 4 and resume Phase 5 at the first non-archived task.
This lets /opsr:flow pick up an interrupted change instead of recreating planning artifacts.

## Pacing
Pause for user confirmation between planning phases (1–4) when scope is ambiguous; once tasks are
agreed, Phase 5 can run task-by-task with a trace after each.

## Output
- A fully executed change: all planning artifacts archived, deltas synced, code implemented.

## Important rules
- Delegate each phase to its skill — never inline another skill's workflow into this one.
- Honor every phase gate (validation, harness checklists) as defined by the delegated skill.
- Implementation code is written to local files; planning artifacts live only in the database.
`,
};
