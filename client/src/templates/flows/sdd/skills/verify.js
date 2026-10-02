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

### Step 5 — Verify test_status (TDD gate)
Walk every \`test\` artifact linked (directly or transitively) to the change. The point is to derive a fresh \`test_status\` for scenario-level tests and to fail the verification on any non-exempt test that is not green.

1. **Collect every \`test\` artifact linked to the change.** Start from the change's task list (use \`get_relationships(name="<change-name>-design", project_slug="${slug}")\` plus a loop over each \`task-name\`) and follow \`implements\` / \`relates_to\` links to gather all \`type="test"\` artifacts reachable from the change's tasks and specs. Also follow design \`relates_to\` scenario tests so coverage analysis is holistic.
2. **For each scenario-level test** (\`metadata.level="scenario"\`), recompute \`test_status\` from its linked unit-level tests:
   - \`passing\` if at least one linked unit test exists and every one of them has \`test_status="passing"\`.
   - \`failing\` if any linked unit test has \`test_status="failing"\`.
   - \`pending\` if the scenario has zero linked unit tests yet.
   Then \`update_artifact(name="<scenario-test>", metadata={"test_status": "<derived>"}, project_slug="${slug}")\` so the recomputed status is persisted and visible in semantic search.
3. **Classify each test** by its current \`test_status\`. A test is \`exempt\` only if its linked task carries \`metadata.test_exempt=true\` AND the task's content states a reason (the same gate \`validate_artifact\` applies — see sdd-workflow-lifecycle REQ-005). Otherwise it counts as a non-exempt test.
4. **Collect blockers.** Every non-exempt test whose \`test_status\` is not exactly \`"passing"\` is a **CRITICAL: Test <name> not passing (<test_status>)** issue. Group them at the top of the report so the agent and the user see the failure first.
5. **Scenario derivation is in-scope here.** The previous applies of \`/opsr:apply\` updated unit-level \`test_status\`, but scenario-level \`test_status\` is derived (not authored) — this step is the one place the value gets computed for the change.

${harnessChecklistBlock(slug, "on_verify", "Declaring verification complete")}
### Step 6 — Generate the report
\`\`\`
## Verification Report: <change-name>

### Summary
| Dimension    | Status |
|--------------|--------|
| Completeness | ✓/✗   |
| Correctness  | ✓/✗   |
| Coherence    | ✓/✗   |
| Tests        | ✓/✗ (<N> blocking, <M> passing) |

### CRITICAL Issues
- [Issue]
- [Test <name> not passing (<status>) ...]   ← from Step 5

### WARNING Issues
- [Issue]

### SUGGESTIONS
- [Issue]

### Assessment
[READY TO ARCHIVE | ISSUES MUST BE FIXED BEFORE ARCHIVING]
\`\`\`

The "Tests" row reflects Step 5. **Do NOT write "READY TO ARCHIVE" while any CRITICAL test issue (or any other CRITICAL issue) remains.** \`/opsr:archive\` will be blocked by the harness rule \`tdd-first\` if any non-exempt test artifact linked to the change has \`test_status\` other than \`"passing"\`, so the report's assessment MUST agree with that gate to avoid a misleading recommendation.

### Step 7 — Record the verification
\`record_trace(action="verify", result_summary="Verification: <PASS/FAIL> — <N> critical, <N> warnings, <M> test blockers", project_slug="${slug}")\`

## Output
- A structured verification report (CRITICAL / WARNING / SUGGESTION). No artifacts are modified.

## Important rules
- This phase is READ-ONLY for artifacts — never change task or spec status here.
- Run the harness checklist (on_verify) before declaring verification complete.
- A change is not ready to archive while any CRITICAL issue remains.
`,
};
