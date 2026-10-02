import { harnessChecklistBlock } from "./_shared.js";

export const applySkill = {
  name: "opensddrag-apply",
  description:
    "Implement the next pending task against spec acceptance criteria",
  body: (slug, note) => `# OpenSddRag — Apply
${note}## When to use
To implement tasks one at a time, validating each against its spec acceptance criteria before
marking it done. Read the design (and, per task, the spec it implements) as context — the
proposal is not re-read during apply, since the design already encodes its decisions.

## Inputs
$ARGUMENTS = change name, or a specific task name.

## Workflow

### Step 1 — Load implementation context
1. Load the working context:
   \`get_working_context(project_slug="${slug}")\`
2. Fetch the list of all artifacts to serve as the freshness oracle:
   \`list_artifacts(project_slug="${slug}")\`
3. Retrieve the change's design content (\`<change-name>-design\`):
   - Locate the design artifact in the \`list_artifacts\` results to get its \`id\` and \`updated_at\`.
   - If no design exists, output "Design missing for change '<change-name>'. Run /opsr:design before /opsr:apply." and STOP.
   - Look up the design's \`id\` in the working context's \`context.content_cache\` (if present):
     - **CACHE HIT:** If the cache entry exists and its \`updated_at\` matches the oracle's \`updated_at\`, use the cached design content. Do not call \`read_artifact\`.
     - **CACHE MISS/STALE:** If the cache entry is missing or its \`updated_at\` does not match, call \`read_artifact(name="<change-name>-design", project_slug="${slug}")\`. Then, update the working context cache by calling \`update_working_context\` with \`context.content_cache[<artifact_id>] = {type: "design", content: "<content>", updated_at: "<updated_at>"}\`.
4. Do NOT read the proposal during apply — its rationale is already captured in the design.
5. Read the specific spec a task implements pointwise at validation time (Step 6) using the same caching logic (check cache, hit → use, miss/stale → read and cache). Tasks themselves are never cached.

### Step 2 — List pending tasks
\`list_artifacts(type="task", status="active", project_slug="${slug}")\`
\`list_artifacts(type="task", status="draft", project_slug="${slug}")\`
Combine both; filter by metadata.change_name. Prioritize \`active\` (resuming) then \`draft\` in dependency order.

### Step 3 — Select the next task
If $ARGUMENTS names a task, use it. Otherwise:
1. Prefer any task with status="active" (interrupted session).
2. Else pick the first draft task whose dependencies are all archived.
\`read_artifact(name="<task-name>", project_slug="${slug}")\`

### Step 4 — Mark the task active
\`update_artifact(name="<task-name>", status="active", project_slug="${slug}")\`
\`update_working_context(context={"current_task": "<task-name>"}, project_slug="${slug}")\`

### Step 5 — Implement the task (RED → GREEN → REFACTOR per testable unit)
The task's acceptance criteria were decomposed into one or more unit-level \`test\` artifacts by \`/opsr:tasks\` (Step 3.2 in that skill). Every \`test\` artifact linked to this task via \`implements\` defines one testable unit you MUST drive through the micro-cycle below. The cycle is **stack-agnostic** — describe the behaviour the test asserts, not the runner's CLI; whichever test runner the target project uses (pytest, vitest, jest, go test, etc.) the discipline is the same.

For each linked unit-level \`test\` artifact, in order:

1. **Read the test artifact** for the unit it covers:
   \`read_artifact(name="<test-artifact-name>", project_slug="${slug}")\`
2. **RED — write the failing test first.** In the target project's test directory, write the test that asserts the behaviour described in the \`test\` artifact's content. Run the test using the project's native runner; confirm it fails for the right reason (the assertion is wrong because the code doesn't exist yet). Then update the \`test\` artifact:
   \`update_artifact(name="<test-artifact-name>", metadata={"test_status": "failing"}, project_slug="${slug}")\`
   Do NOT write any production code before this step completes. If you find yourself about to "stub" production code to make the test compile, that's still production code — back up and finish RED with the test failing for the right reason.
3. **GREEN — minimal implementation.** Write the smallest amount of production code that makes the failing test pass. Re-run the test; confirm it now passes. Then update the \`test\` artifact:
   \`update_artifact(name="<test-artifact-name>", metadata={"test_status": "passing"}, project_slug="${slug}")\`
4. **REFACTOR — clean up while staying green.** With the test green, refactor the production code (and/or the test) for clarity, naming, or duplication. Re-run the test after every refactor. \`test_status\` MUST remain \`"passing"\` throughout — if a refactor regresses the test, fix it before moving on. The \`test_status\` field on the artifact is updated to \`"passing"\` once after REFACTOR (or earlier, after GREEN) and stays \`"passing"\`.
5. Repeat steps 1-4 for the next linked unit until every unit-level \`test\` artifact is \`test_status="passing"\`. If the task is \`metadata.test_exempt=true\` (e.g. prompt template, SQL migration), it has no linked units — Step 5 is a no-op and you move directly to Step 6.

The code changes (Edit/Write/Bash on local files) are the expected output of this step, exactly as before. The difference is that they are gated by the per-unit RED → GREEN → REFACTOR loop and accompanied by the \`test_status\` updates on the linked artifacts.

### Step 6 — Validate against spec requirements AND test status
For each acceptance criterion (REQ-NNN) the task implements, confirm the implementation satisfies it and no spec scenario is broken. Then walk the task's linked unit-level \`test\` artifacts (use \`get_relationships(name="<task-name>", project_slug="${slug}")\`) and confirm every one of them has \`metadata.test_status="passing"\`. If any is still \`"failing"\` or \`"pending"\`, STOP and return to Step 5 to finish that unit's cycle — the harness rule \`tdd-first\` will block archive otherwise.

Only when every unit-level \`test\` is \`"passing"\` (or the task is \`test_exempt\`) should Step 7 run.

### Step 7 — Falsify the change
For every symbol, value, or file touched in Step 5, actively try to prove the change incomplete: search the affected code/config for other call sites, importers, config consumers, or re-exports using Read/Grep/Bash — not a re-read of the proposal, design, or full specs bundle. If a consumer also needs updating, fix it now and re-run Step 6 against it. If none are found, proceed. This step targets the codebase, not the SDD planning artifacts, and must not become a reason to widen the Step 1 minimal-read floor.

This step is **unchanged** from the form shipped by \`apply-verify-before-done\` — it addresses hidden dependencies elsewhere in the codebase, a different concern from a unit's own correctness. Do not fold it into REFACTOR and do not widen its scope.

${harnessChecklistBlock(slug, "on_apply", "Marking the task archived")}
### Step 8 — Mark the task done
\`update_artifact(name="<task-name>", status="archived", project_slug="${slug}")\`

### Step 9 — Record and check remaining work
\`record_trace(action="apply_task", result_summary="Completed task: <task-name>", artifact_id="<artifact-id>", project_slug="${slug}")\`
\`list_artifacts(type="task", status="draft", project_slug="${slug}")\`
- If tasks remain: "Task complete. Run /opsr:apply <change-name> for the next task."
- If all done: "All tasks complete. Run /opsr:verify <change-name>, then /opsr:archive <change-name>."

## Output
- Code changes on disk satisfying the task's acceptance criteria.
- Task status advanced draft → active → archived in the database.

## Important rules
- Read the design and the task's spec before implementing — never code from the task alone. Do not re-read the proposal during apply.
- Before marking a task archived, run Step 7 (falsify the change): trace usages/dependencies of whatever changed instead of assuming the initial minimal read was sufficient. Keep this to codebase tracing — it is not a reason to re-read the proposal/design/specs bundle.
- Run the harness checklist (on_apply) BEFORE marking a task archived; STOP on any error-severity rule.
- One task at a time; do not batch-archive tasks.
`,
};
