export const syncSkill = {
  name: "opensddrag-sync",
  description: "Merge delta specs back into main capability specs",
  body: (slug, note) => `# OpenSddRag — Sync
${note}## When to use
To merge delta specs (ADDED/MODIFIED/REMOVED/RENAMED) into the main specs stored in the database.
Delta specs are created by /opsr:spec for MODIFIED capabilities. Runs automatically during /opsr:archive.

## Inputs
$ARGUMENTS = change name.

## Workflow

### Step 1 — Find delta specs for this change
\`list_artifacts(type="spec", project_slug="${slug}")\`
Filter where metadata.change_name = "<change-name>" AND metadata.is_delta = true.

### Step 2 — For each delta, find the main spec
\`search_semantic(query="<capability> spec", project_slug="${slug}", limit=5)\`
Find the spec for the same capability where metadata.is_delta = false (or unset).

### Step 3 — Apply delta operations to the main spec
\`read_artifact(name="<delta-spec>", project_slug="${slug}")\`
\`read_artifact(name="<main-spec>", project_slug="${slug}")\`
Apply each delta section:
- **## ADDED Requirements** → confirm the requirement does NOT exist, then append it (with scenarios).
- **## MODIFIED Requirements** → find by name and apply ONLY the changed parts (partial update, not wholesale replace).
- **## REMOVED Requirements** → remove the requirement block; note the Reason/Migration in a comment.
- **## RENAMED Requirements** → change the heading FROM the old name TO the new name.

### Step 4 — Save the updated main spec
\`update_artifact(name="<main-spec>", content="<merged spec content>", project_slug="${slug}")\`

### Step 5 — Archive the delta spec
\`update_artifact(name="<delta-spec>", status="archived", metadata={"synced_at": "<ISO timestamp>", "merged_into": "<main-spec>"}, project_slug="${slug}")\`

### Step 6 — Record the sync
\`record_trace(action="sync", result_summary="Synced delta for capability: <capability> into main spec", project_slug="${slug}")\`
Tell the user which capabilities were updated.

## Worked example — a MODIFIED merge
Delta says:
\`\`\`markdown
## MODIFIED Requirements
### Requirement: REQ-002 Token issuance
[adds a new scenario for refresh tokens]
\`\`\`
Main spec already has REQ-002 with two scenarios. Correct merge = keep the existing two scenarios
and APPEND the new refresh-token scenario under the same requirement heading. Do NOT replace the
whole REQ-002 block — that would silently drop the original scenarios.

## When NOT to sync
- The delta is still being edited (run /opsr:spec to completion first).
- No main spec exists yet for the capability — then there is nothing to merge into; the delta
  IS the spec until a main is created.

## Output
- Main spec artifacts updated to reflect all deltas; delta specs archived with a merge pointer.

## Important rules
- MODIFIED requirements get partial, intelligent merges — never blind whole-section replacement.
- Always archive the delta after merging so it is not re-applied.
- Preserve REMOVED requirements' Reason/Migration as a note for future readers.
`,
};
