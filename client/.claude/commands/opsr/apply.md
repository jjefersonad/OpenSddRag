> **IMPORTANT — /opsr:apply**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Implement tasks one by one, validating each against the spec acceptance criteria before marking done.
Read ALL planning artifacts (proposal, specs, design) as context before implementing any task.

## Input
$ARGUMENTS = change name, or specific task name.

## Step 1 — Load full planning context from the database
`get_working_context(project_slug="test-change")`
`read_artifact(name="<change-name>-proposal", project_slug="test-change")`
`read_artifact(name="<change-name>-design", project_slug="test-change")`
Get and read all specs linked to this change.

## Step 2 — List pending tasks in order
`list_artifacts(type="task", status="draft", project_slug="test-change")`
AND
`list_artifacts(type="task", status="active", project_slug="test-change")`
Combine both results. Prioritize tasks with status="active" (resuming interrupted session), then status="draft" in dependency order. Filter tasks for this change using metadata.change_name.

## Step 3 — Select next task
If $ARGUMENTS specifies a task name, use it.
Otherwise:
1. First, check for tasks with status="active" (resuming interrupted session)
2. If no active tasks, pick the first draft task whose dependencies are all archived (done)

Read the task:
`read_artifact(name="<task-name>", project_slug="test-change")`

## Step 4 — Mark task as active in database
`update_artifact(name="<task-name>", status="active", project_slug="test-change")`
Update working context:
`update_working_context(context={"current_task": "<task-name>"}, project_slug="test-change")`

## Step 5 — Implement the task
Implement the code changes required by the task.
The implementation MUST satisfy all acceptance criteria from the task's "## Acceptance Criteria" section.
Pause and ask the user if any requirement is unclear — do not guess.

## Step 6 — Validate against spec requirements
For each acceptance criterion (REQ-NNN) in the task:
- Confirm the implementation satisfies the requirement
- Verify no spec scenarios are broken

## Step 7 — Mark task as done in database
`update_artifact(name="<task-name>", status="archived", project_slug="test-change")`

## Step 8 — Record and check remaining tasks
`record_trace(action="apply_task", result_summary="Completed task: <task-name>", artifact_id="<artifact-id>", project_slug="test-change")`
`list_artifacts(type="task", status="draft", project_slug="test-change")`
- If tasks remain: "Task complete. Run `<opsr:apply <change-name>` for the next task."
- If all done: "All tasks complete. Run `<opsr:verify <change-name>` to validate, then `<opsr:archive <change-name>`."
