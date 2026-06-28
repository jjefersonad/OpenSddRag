import { harnessChecklistBlock } from "./_shared.js";

export const verifySkill = {
  name: "opensddrag-verify",
  description:
    "Validate implementation against spec requirements and design decisions",
  body: (slug, note) => `# OpenSddRag — Verify
${note}## When to use
After all tasks are implemented, to validate the implementation against spec requirements and
design decisions. Read-only — produces a structured report and modifies no artifacts.

## Inputs
$ARGUMENTS = change name.

## Workflow

### Step 1 — Load the change bundle
\`read_change_bundle(change_name="<change-name>", project_slug="${slug}")\`
Verification is holistic, so load everything in one call. The response carries the
proposal, design, full specs, and a task list (\`tasks[] = {name, status}\`) with
\`task_count\`. If \`task_count\` does not equal the number of returned task entries,
report an **incomplete bundle** for the change and STOP before declaring verification
complete. Otherwise proceed — do **not** issue additional \`read_artifact\` calls for
the proposal, design, or specs.

### Step 2 — Verify COMPLETENESS
From the bundle's \`tasks[]\`, treat any task whose \`status\` is not \`archived\` as pending.
- If pending tasks exist → **CRITICAL: Tasks not complete**.
Extract every REQ-NNN from the bundle's specs and search the codebase for implementation evidence.
- If a requirement has no evidence → **CRITICAL: Requirement not implemented**.

### Step 3 — Verify CORRECTNESS
For each spec scenario (WHEN/THEN), search for test coverage or implementation of the condition.
- If a scenario has no coverage → **WARNING: Scenario not covered**.

### Step 4 — Verify COHERENCE
Extract decisions from the design's "## Decisions" section. For each:
- Check the implementation follows the chosen approach.
- If it deviates → **SUGGESTION: Possible deviation from design**.

${harnessChecklistBlock(slug, "on_verify", "Declaring verification complete")}
### Step 5 — Generate the report
\`\`\`
## Verification Report: <change-name>

### Summary
| Dimension    | Status |
|--------------|--------|
| Completeness | ✓/✗   |
| Correctness  | ✓/✗   |
| Coherence    | ✓/✗   |

### CRITICAL Issues
- [Issue]

### WARNING Issues
- [Issue]

### SUGGESTIONS
- [Issue]

### Assessment
[READY TO ARCHIVE | ISSUES MUST BE FIXED BEFORE ARCHIVING]
\`\`\`

### Step 6 — Record the verification
\`record_trace(action="verify", result_summary="Verification: <PASS/FAIL> — <N> critical, <N> warnings", project_slug="${slug}")\`

## Output
- A structured verification report (CRITICAL / WARNING / SUGGESTION). No artifacts are modified.

## Important rules
- This phase is READ-ONLY for artifacts — never change task or spec status here.
- Run the harness checklist (on_verify) before declaring verification complete.
- A change is not ready to archive while any CRITICAL issue remains.
`,
};
