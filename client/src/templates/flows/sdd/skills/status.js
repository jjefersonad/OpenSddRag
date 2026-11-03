export const statusSkill = {
  name: "opensddrag-status",
  description: "Show current state of all in-progress changes",
  body: (slug, note) => `# OpenSddRag — Status
${note}## When to use
To show the current state of all in-progress changes for this project: artifact completion,
task progress, and recent activity. Reads from the MCP server — no local files involved.

## Inputs
$ARGUMENTS = optional change name to show details for a single change. If absent, show all.

## Workflow

### Step 1 — Load working context
\`get_working_context(project_slug="${slug}")\`
This also surfaces any \`trigger="always"\` harness rules — read them first.

### Step 2 — List artifacts by type and status
\`list_artifacts(type="proposal", status="active", project_slug="${slug}")\`
\`list_artifacts(type="proposal", status="draft", project_slug="${slug}")\`
\`list_artifacts(type="spec", status="active", project_slug="${slug}")\`
\`list_artifacts(type="design", status="active", project_slug="${slug}")\`
\`list_artifacts(type="task", status="active", project_slug="${slug}")\`
\`list_artifacts(type="task", status="draft", project_slug="${slug}")\`

### Step 3 — Recall recent activity
\`recall_episodes(query="recent actions in this project", project_slug="${slug}", limit=5)\`

### Step 4 — Present a structured status
For each active change, show:
\`\`\`
## Change: <change-name>
| Artifact | Status |
|----------|--------|
| Proposal | ✓ done |
| Specs    | ✓ 2/2  |
| Design   | ✓ done |
| Tasks    | 3/5 done |

Current task: <task-name>
Next step: /opsr:apply <change-name>
\`\`\`
Then show recent activity (last 5 episodes) and a suggested next command based on the state.

### Step 5 — Suggest the next command
Map the change's state to the next action:
- proposal only → /opsr:spec
- specs but no design → /opsr:design
- design but no tasks → /opsr:tasks
- tasks with drafts remaining → /opsr:apply
- all tasks archived → /opsr:verify then /opsr:archive

## Reading the working context
\`get_working_context\` returns \`current_task\` and the ordered \`tasks\` list — use them to compute
"N/M done" and to name the in-flight task. It also returns always-trigger harness rules; show
those at the top so the user starts every session aware of the project's constraints.

## Output
- A per-change status table, recent activity, and the recommended next command.

## Important rules
- Read-only — never modify artifacts from status.
- If a specific change is requested, scope all lists to that change via metadata.change_name.
- Always surface always-trigger harness rules from the working context.
`,
};
