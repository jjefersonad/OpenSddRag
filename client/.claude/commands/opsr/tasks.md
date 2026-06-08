> **IMPORTANT — /opsr:tasks**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Decompose the specs and design into atomic, verifiable task artifacts.
Each task must map to one or more spec requirements (REQ-NNN) and be completable in under 4 hours.
Tasks depend on BOTH specs AND design being in the database.

## Input
$ARGUMENTS = change name.

## Step 1 — Read all planning artifacts from the database
`read_artifact(name="<change-name>-proposal", project_slug="test-change")`
`read_artifact(name="<change-name>-design", project_slug="test-change")`
Get all specs for this change:
`get_relationships(name="<change-name>-proposal", project_slug="test-change")`
Read each linked spec artifact.

## Step 2 — Plan task groups from the design and specs
Group tasks by logical phase. Each task must have:
- A clear **Goal** (what it accomplishes)
- **Acceptance criteria** referencing spec REQ-NNN items (not vague)
- **Dependencies** on other tasks (if any)
- Estimated effort: < 4 hours

## Step 3 — Create each task artifact in the database
For each task (name as `<change-name>-task-<group>-<N>`):
`create_artifact(name="<change-name>-task-<group>-<N>", type="task", content="## Goal\n<what this task accomplishes>\n\n## Acceptance Criteria\n- [ ] REQ-NNN: <criterion>\n- [ ] <criterion>\n\n## Dependencies\n- <other task name or 'none'>", metadata={"change_name": "<change-name>", "group": "<group-name>", "order": <N>}, project_slug="test-change")`

## Step 4 — Link each task to its spec(s)
`link_artifacts(source_name="<task-name>", target_name="<spec-name>", relationship_type="implements", project_slug="test-change")`

## Step 5 — Update working context with the task list
`update_working_context(context={"change_name": "<change-name>", "tasks": ["<task-1>", "<task-2>", "..."], "current_task": null}, project_slug="test-change")`

## Step 6 — Record and show next steps
`record_trace(action="tasks", result_summary="Created <N> tasks for <change-name>", project_slug="test-change")`
Show the full task list with names and goals.
Tell the user: "Tasks saved. Run `<opsr:apply <change-name>` to start implementing."
