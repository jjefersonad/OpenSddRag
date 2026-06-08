> **IMPORTANT — /opsr:sync**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Merge delta specs (ADDED/MODIFIED/REMOVED/RENAMED sections) into the main specs stored in the database.
Delta specs are created by /opsr:spec for MODIFIED capabilities.
After sync, the main spec reflects all changes. This is called automatically during /archive.

## Input
$ARGUMENTS = change name.

## Step 1 — Find delta specs for this change
`list_artifacts(type="spec", project_slug="test-change")`
Filter specs where metadata.change_name = "<change-name>" AND metadata.is_delta = true.

## Step 2 — For each delta spec, find the main spec
Search for the main (non-delta) spec for the same capability:
`search_semantic(query="<capability-name> spec", project_slug="test-change", limit=5)`
Find the spec where metadata.is_delta = false (or not set) for the same capability.

## Step 3 — Apply delta operations to the main spec
Read both delta and main spec:
`read_artifact(name="<delta-spec-name>", project_slug="test-change")`
`read_artifact(name="<main-spec-name>", project_slug="test-change")`

Apply each section from the delta:

**## ADDED Requirements:**
- Find or confirm the requirement does NOT exist in main spec
- Append the new requirement (with all scenarios) to the main spec

**## MODIFIED Requirements:**
- Find the requirement in main spec by name
- Apply ONLY the changed parts (add new scenarios, update descriptions)
- Do NOT wholesale replace — apply partial updates intelligently

**## REMOVED Requirements:**
- Find the requirement in main spec by name
- Remove the entire requirement block
- The Reason and Migration from delta should be noted in a comment

**## RENAMED Requirements:**
- Find FROM name in main spec
- Change the heading to TO name

## Step 4 — Save the updated main spec to database
`update_artifact(name="<main-spec-name>", content="<merged spec content>", project_slug="test-change")`

## Step 5 — Mark delta spec as archived
After merging the delta, mark the delta spec as archived:
`update_artifact(name="<delta-spec-name>", status="archived", metadata={"synced_at": "<ISO timestamp>", "merged_into": "<main-spec-name>"}, project_slug="test-change")`

## Step 6 — Record the sync
`record_trace(action="sync", result_summary="Synced delta for capability: <capability> into main spec", project_slug="test-change")`
Tell the user which capabilities were updated.
