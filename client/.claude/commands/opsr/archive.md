> **IMPORTANT — /opsr:archive**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Finalize a completed change by archiving all its artifacts.
Runs verification checks, syncs delta specs to main specs, then archives everything.

## Input
$ARGUMENTS = change name. If not provided, list active changes and ask.

## Step 1 — Get full status of the change
`list_artifacts(type="proposal", project_slug="test-change")`
Select the change to archive (or use $ARGUMENTS).
`get_relationships(name="<change-name>-proposal", project_slug="test-change")`
Get all linked artifacts (specs, design, tasks).

## Step 2 — Validate artifact completion
Check each artifact status:
`list_artifacts(type="task", status="draft", project_slug="test-change")`
If pending tasks exist → warn the user and ask for confirmation to archive anyway.

## Step 3 — Validate task completion
Count draft vs archived tasks. If any draft tasks remain → warn and confirm.

## Step 4 — Check for delta specs that need syncing
`list_artifacts(type="spec", project_slug="test-change")`
Filter for specs where metadata.change_name = "<change-name>" AND metadata.is_delta = true.

If delta specs exist:
- Show which capabilities have deltas
- Ask: "Sync delta specs to main specs now? (recommended)"
- If yes → execute <opsr:sync logic for each delta spec
- If no → archive without syncing

## Step 5 — Archive all change artifacts
For each artifact in this change (proposal, all specs, design, all tasks):
`update_artifact(name="<artifact-name>", status="archived", metadata={"archived_at": "<ISO timestamp>", "change_name": "<change-name>"}, project_slug="test-change")`

## Step 6 — Record and show summary
`record_trace(action="archive", result_summary="Archived change: <change-name> (<N> artifacts)", project_slug="test-change")`
Show summary:
- Artifacts archived: list
- Specs synced: list (if any)
- "Change <change-name> is complete."
