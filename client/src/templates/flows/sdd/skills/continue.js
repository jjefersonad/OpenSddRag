export const continueSkill = {
  name: "opensddrag-continue",
  description: "Create the next single artifact in the SDD dependency chain",
  body: (slug, note) => `# OpenSddRag — Continue
${note}## When to use
To create the NEXT SINGLE artifact in the dependency chain for a change and then stop. Unlike
/opsr:flow (which creates everything), this advances exactly one step per invocation.

Dependency order: proposal → specs → design → tasks.

## Inputs
$ARGUMENTS = change name.

## Workflow

### Step 1 — Get the current status
\`list_artifacts(type="proposal", project_slug="${slug}")\`
\`get_relationships(name="<change-name>-proposal", project_slug="${slug}")\`
Gather all existing artifacts for this change.

### Step 2 — Find the next artifact to create
Walk the dependency order and find the first gap:
1. proposal → if missing, stop and tell the user to run /opsr:propose first.
2. specs → if any capability has no spec → the next artifact is ONE spec.
3. design → if missing and all specs exist → the next artifact is the design.
4. tasks → if missing and the design exists → the next artifacts are the tasks.

If every artifact already exists → tell the user "All planning artifacts complete. Run /opsr:apply."

### Step 3 — Create the NEXT artifact only, by delegating to the matching skill
Do NOT inline the workflow here — load the corresponding skill and follow it for a single artifact:
- next = spec → load the \`opensddrag-spec\` skill and create ONE capability's spec.
- next = design → load the \`opensddrag-design\` skill and create the design.
- next = tasks → load the \`opensddrag-tasks\` skill and create the tasks.
Then STOP — do not proceed to the following artifact in this invocation.

### Step 4 — Show progress
- Show what was created.
- Show what is now unlocked (next in the dependency chain).
- Suggest: "Run /opsr:continue <change-name> to create the next artifact."

## Worked example
Given a change with a proposal and 2 of 3 capabilities specced:
1. Step 2 detects the gap: one capability still has no spec.
2. Step 3 loads \`opensddrag-spec\` and creates ONLY that capability's spec, then stops.
3. Step 4 reports "spec created (3/3). Next: design. Run /opsr:continue <change-name>."

Next invocation detects all specs exist but no design → creates the design and stops. And so on
until tasks exist, at which point it directs the user to /opsr:apply.

## Why one step at a time
/opsr:continue is for reviewing each artifact before the next is generated. When you want the
whole chain produced in one pass without pausing, use /opsr:flow instead.

## Output
- Exactly one new artifact (or one batch of tasks), advancing the change by a single step.

## Important rules
- Create ONE artifact (or the single tasks batch) per invocation, then stop.
- Delegate the actual artifact creation to the matching skill — never duplicate its steps here.
- Respect dependency order; never skip a missing upstream artifact.
`,
};
