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

### Step 5 — Implement the task
Write the code changes required by the task using Edit/Write/Bash (local files — this is expected).
The implementation MUST satisfy every acceptance criterion. Pause and ask if anything is unclear — do not guess.

### Step 6 — Validate against spec requirements
For each acceptance criterion (REQ-NNN): confirm the implementation satisfies it and no spec scenario is broken.

${harnessChecklistBlock(slug, "on_apply", "Marking the task archived")}
### Step 7 — Mark the task done
\`update_artifact(name="<task-name>", status="archived", project_slug="${slug}")\`

### Step 8 — Record and check remaining work
\`record_trace(action="apply_task", result_summary="Completed task: <task-name>", artifact_id="<artifact-id>", project_slug="${slug}")\`
\`list_artifacts(type="task", status="draft", project_slug="${slug}")\`
- If tasks remain: "Task complete. Run /opsr:apply <change-name> for the next task."
- If all done: "All tasks complete. Run /opsr:verify <change-name>, then /opsr:archive <change-name>."

## Output
- Code changes on disk satisfying the task's acceptance criteria.
- Task status advanced draft → active → archived in the database.

## Important rules
- Read the design and the task's spec before implementing — never code from the task alone. Do not re-read the proposal during apply.
- Run the harness checklist (on_apply) BEFORE marking a task archived; STOP on any error-severity rule.
- One task at a time; do not batch-archive tasks.
`,
};
