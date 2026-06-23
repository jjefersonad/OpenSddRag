import { harnessChecklistBlock } from "./_shared.js";

export const applySkill = {
  name: "opensddrag-apply",
  description:
    "Implement the next pending task against spec acceptance criteria",
  body: (slug, note) => `# OpenSddRag — Apply
${note}## When to use
To implement tasks one at a time, validating each against its spec acceptance criteria before
marking it done. Read ALL planning artifacts (proposal + specs + design) as context first.

## Inputs
$ARGUMENTS = change name, or a specific task name.

## Workflow

### Step 1 — Load full planning context
\`get_working_context(project_slug="${slug}")\`
\`read_artifact(name="<change-name>-proposal", project_slug="${slug}")\`
\`read_artifact(name="<change-name>-design", project_slug="${slug}")\`
Get and read all specs linked to this change.

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
- Read ALL planning artifacts before implementing — never code from the task alone.
- Run the harness checklist (on_apply) BEFORE marking a task archived; STOP on any error-severity rule.
- One task at a time; do not batch-archive tasks.
`,
};
