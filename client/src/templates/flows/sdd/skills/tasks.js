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

For each task, also identify its **testable units** — the discrete methods/functions/behaviours that an implementer will cover in the apply phase. Rule of thumb: each Acceptance Criterion that maps to a runnable unit becomes one testable unit. If the task has zero testable units (e.g. prompt template, SQL migration, doc edit), flag it as \`test_exempt\` and write a one-line \`## Reason\` heading in the content explaining why no unit applies (see Step 3 escape hatch below).

### Step 3 — Create each task artifact AND its unit-level test artifact(s)
The task and its \`test\` artifacts MUST be created together so the new REQ-005 validation check (test link required) passes on the first try. The order is:

1. **Create the task artifact first**, without calling \`validate_artifact\` yet. Use this template:
   \`create_artifact(name="<change-name>-task-<group>-<N>", type="task", content="## Goal\\n<what this task accomplishes>\\n\\n## Acceptance Criteria\\n- [ ] REQ-NNN: <criterion>\\n- [ ] <criterion>\\n\\n## Dependencies\\n- <other task name or 'none'>", metadata={"change_name": "<change-name>", "group": "<group>", "order": <N>}, project_slug="${slug}")\`

2. **For each testable unit identified in Step 2**, create a linked \`test\` artifact (\`type="test"\`, \`level="unit"\`, \`test_status="pending"\`):
   \`create_artifact(name="<change-name>-task-<group>-<N>-unit-<k>", type="test", content="<unit-level scenario the test will exercise — what the test must prove, in WHEN/THEN form or as a short prose contract>", metadata={"change_name": "<change-name>", "group": "<group>", "order": <N>, "task_name": "<change-name>-task-<group>-<N>", "level": "unit", "requirement_ref": "REQ-NNN", "test_status": "pending"}, project_slug="${slug}")\`

3. **Link each test artifact back to the task** via \`implements\` (this is the relationship the REQ-005 validator counts):
   \`link_artifacts(source_name="<change-name>-task-<group>-<N>", target_name="<change-name>-task-<group>-<N>-unit-<k>", relationship_type="implements", project_slug="${slug}")\`

4. **Escape hatch for un-testable tasks.** If the task has no testable unit, do NOT create a \`test\` artifact. Instead, set \`metadata.test_exempt=true\` on the task at creation time AND prepend a \`## Reason\` heading to the content so the validator's exempt path can find it:
   \`create_artifact(name="<change-name>-task-<group>-<N>", type="task", content="## Reason\\n<why no testable unit applies — e.g. 'Prompt template only, no runtime behaviour', 'SQL migration without standalone logic', 'Doc edit only'>\\n\\n## Goal\\n<what this task accomplishes>\\n\\n## Acceptance Criteria\\n- [ ] REQ-NNN: <criterion>\\n\\n## Dependencies\\n- <other task name or 'none'>", metadata={"change_name": "<change-name>", "group": "<group>", "order": <N>, "test_exempt": true}, project_slug="${slug}")\`

5. **Then** run \`validate_artifact\` on the task. By that point the linked tests (or the \`test_exempt\` reason) are already in place, so REQ-005 should pass on the first try:
   \`validate_artifact(name="<change-name>-task-<group>-<N>", project_slug="${slug}")\` — fix any issues, then move on.

### Step 4 — Link each task to its spec(s)
\`link_artifacts(source_name="<task-name>", target_name="<spec-name>", relationship_type="implements", project_slug="${slug}")\`

### Step 5 — Update working context with the task list
\`update_working_context(context={"change_name": "<change-name>", "tasks": ["<task-1>", "<task-2>", "..."], "current_task": null}, project_slug="${slug}")\`

### Step 6 — Record and show next steps
\`record_trace(action="tasks", result_summary="Created <N> tasks for <change-name> with linked unit-level test artifacts", project_slug="${slug}")\`
Show the full task list with names and goals, then tell the user:
"Tasks saved. Run /opsr:apply <change-name> to start implementing."

## Example task artifact (with linked unit-level test)
\`\`\`markdown
## Goal
Add a POST /sessions endpoint that issues a JWT for valid credentials.

## Acceptance Criteria
- [ ] REQ-002: Endpoint returns 200 + token for valid credentials
- [ ] REQ-003: Endpoint returns 401 for invalid credentials

## Dependencies
- <change>-task-db-1 (users table migration)
\`\`\`

Companion \`test\` artifact (\`level=unit\`, \`test_status=pending\`) — one per testable unit:

\`\`\`markdown
Test for unit 'issue_token(valid_credentials)': a valid username/password pair MUST
yield a signed JWT carrying the user's id and an expiry in the future. The test
runs first, fails (RED), then the implementation makes it pass (GREEN).
\`\`\`

Ordering tip: number tasks within a group (\`-task-<group>-<N>\`) so /opsr:apply can walk them
in dependency order. Put migrations and shared scaffolding first, feature work next, tests last
(or alongside, if the team writes tests with the code).

## Output
- One task artifact per unit of work, each linked to its spec(s).
- For each testable unit identified in Step 2, a linked \`test\` artifact (\`level=unit\`,
  \`test_status=pending\`) so the REQ-005 validation check passes on the first call.
- Tasks with no testable unit carry \`metadata.test_exempt=true\` and a \`## Reason\` heading.
- Working context updated with the ordered task list.
- **Unlocks:** /opsr:apply.

## Important rules
- Acceptance criteria MUST reference concrete REQ-NNN items — never "implement the feature".
- Keep each task < 4 hours; split anything larger.
- Tasks are individual database artifacts — NOT a single markdown checklist file.
- Each testable unit identified in Step 2 MUST produce a linked \`test\` artifact (Step 3.2) — do
  not skip this even if the unit feels trivial; the validator counts the link, and the apply
  phase uses the link to drive the RED→GREEN→REFACTOR cycle.
- For tasks with no testable unit, prefer the explicit \`test_exempt\` escape hatch (Step 3.4)
  over a placeholder or trivially-passing test — the rule is "no fake tests".
`,
};
