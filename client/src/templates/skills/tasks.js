export const tasksSkill = {
  name: "opensddrag-tasks",
  description: "Break a design into atomic, verifiable implementation tasks",
  body: (slug, note) => `# OpenSddRag — Tasks
${note}## When to use
After the design exists, to decompose specs + design into atomic, verifiable task artifacts.
Each task maps to one or more spec requirements (REQ-NNN) and is completable in under 4 hours.

## Inputs
$ARGUMENTS = change name.

## Workflow

### Step 1 — Read all planning artifacts
\`read_artifact(name="<change-name>-proposal", project_slug="${slug}")\`
\`read_artifact(name="<change-name>-design", project_slug="${slug}")\`
\`get_relationships(name="<change-name>-proposal", project_slug="${slug}")\`
Read each linked spec artifact.

### Step 2 — Plan task groups
Group tasks by logical phase. Each task MUST have:
- A clear **Goal** (what it accomplishes).
- **Acceptance criteria** referencing spec REQ-NNN items (not vague).
- **Dependencies** on other tasks (if any).
- Estimated effort: < 4 hours.

### Step 3 — Create each task artifact
Name each as \`<change-name>-task-<group>-<N>\`:
\`create_artifact(name="<change-name>-task-<group>-<N>", type="task", content="## Goal\\n<what this task accomplishes>\\n\\n## Acceptance Criteria\\n- [ ] REQ-NNN: <criterion>\\n- [ ] <criterion>\\n\\n## Dependencies\\n- <other task name or 'none'>", metadata={"change_name": "<change-name>", "group": "<group>", "order": <N>}, project_slug="${slug}")\`

### Step 4 — Link each task to its spec(s)
\`link_artifacts(source_name="<task-name>", target_name="<spec-name>", relationship_type="implements", project_slug="${slug}")\`

### Step 5 — Update working context with the task list
\`update_working_context(context={"change_name": "<change-name>", "tasks": ["<task-1>", "<task-2>", "..."], "current_task": null}, project_slug="${slug}")\`

### Step 6 — Record and show next steps
\`record_trace(action="tasks", result_summary="Created <N> tasks for <change-name>", project_slug="${slug}")\`
Show the full task list with names and goals, then tell the user:
"Tasks saved. Run /opsr:apply <change-name> to start implementing."

## Example task artifact
\`\`\`markdown
## Goal
Add a POST /sessions endpoint that issues a JWT for valid credentials.

## Acceptance Criteria
- [ ] REQ-002: Endpoint returns 200 + token for valid credentials
- [ ] REQ-003: Endpoint returns 401 for invalid credentials
- [ ] Unit tests cover both scenarios

## Dependencies
- <change>-task-db-1 (users table migration)
\`\`\`

Ordering tip: number tasks within a group (\`-task-<group>-<N>\`) so /opsr:apply can walk them
in dependency order. Put migrations and shared scaffolding first, feature work next, tests last
(or alongside, if the team writes tests with the code).

## Output
- One task artifact per unit of work, each linked to its spec(s).
- Working context updated with the ordered task list.
- **Unlocks:** /opsr:apply.

## Important rules
- Acceptance criteria MUST reference concrete REQ-NNN items — never "implement the feature".
- Keep each task < 4 hours; split anything larger.
- Tasks are individual database artifacts — NOT a single markdown checklist file.
`,
};
