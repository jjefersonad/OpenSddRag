import { harnessChecklistBlock } from "./_shared.js";

export const archiveSkill = {
  name: "opensddrag-archive",
  description: "Finalize a completed change by archiving all its artifacts",
  body: (slug, note) => `# OpenSddRag — Archive
${note}## When to use
To finalize a completed change: run completion checks, sync delta specs into main specs, then
archive all the change's artifacts.

## Inputs
$ARGUMENTS = change name. If not provided, list active changes and ask.

## Workflow

### Step 1 — Load the change bundle
\`read_change_bundle(change_name="<change-name>", project_slug="${slug}")\`
Archiving sweeps every artifact of the change, so load them all in one call. The
response carries the proposal, design, specs, and the task list
(\`tasks[] = {name, status}\`) with \`task_count\`. Proceed to Step 2.

### Step 2 — Validate artifact completion
From the bundle's \`tasks[]\`, treat any task whose \`status\` is not \`archived\` as pending.
If pending tasks exist → warn the user and ask for confirmation to archive anyway.

### Step 3 — Validate task completion
Count pending vs archived tasks from the bundle. If any non-archived tasks remain → warn and confirm.

### Step 4 — Check for delta specs that need syncing
From the bundle's \`specs[]\`, filter for metadata.change_name = "<change-name>" AND metadata.is_delta = true.
If deltas exist: show the affected capabilities and ask "Sync delta specs to main specs now? (recommended)".
- If yes → run the /opsr:sync workflow (load the opensddrag-sync skill) for each delta.
- If no → archive without syncing.

${harnessChecklistBlock(slug, "on_archive", "Archiving change artifacts")}
### Step 5 — Archive all change artifacts
For each artifact (proposal, all specs, design, all tasks):
\`update_artifact(name="<artifact>", status="archived", metadata={"archived_at": "<ISO timestamp>", "change_name": "<change-name>"}, project_slug="${slug}")\`

### Step 6 — Record and show a summary
\`record_trace(action="archive", result_summary="Archived change: <change-name> (<N> artifacts)", project_slug="${slug}")\`
Show: artifacts archived, specs synced (if any), and "Change <change-name> is complete."

## Output
- Every artifact of the change set to status=archived; deltas merged into main specs.

## Important rules
- Run the harness checklist (on_archive) BEFORE archiving; STOP on any error-severity rule.
- Never archive over pending tasks without explicit user confirmation.
- Sync delta specs before archiving so the main specs stay authoritative.
`,
};
