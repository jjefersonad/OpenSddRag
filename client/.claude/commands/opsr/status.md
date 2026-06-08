> **IMPORTANT — /opsr:status**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Show the current state of all in-progress changes for this project.
Reads from the MCP server — no local files involved.

## Input
$ARGUMENTS = optional change name to show details for one change. If not provided, show all.

## Step 1 — Load working context
`get_working_context(project_slug="test-change")`

## Step 2 — List all artifacts by type and status
`list_artifacts(type="proposal", status="draft", project_slug="test-change")`
`list_artifacts(type="proposal", status="active", project_slug="test-change")`
`list_artifacts(type="spec", status="draft", project_slug="test-change")`
`list_artifacts(type="design", status="draft", project_slug="test-change")`
`list_artifacts(type="task", status="draft", project_slug="test-change")`
`list_artifacts(type="task", status="active", project_slug="test-change")`

## Step 3 — Recall recent activity
`recall_episodes(query="recent actions in this project", project_slug="test-change", limit=5)`

## Step 4 — Present structured status

For each active change, show:
```
## Change: <change-name>
| Artifact | Status |
|----------|--------|
| Proposal | ✓ done |
| Specs    | ✓ 2/2  |
| Design   | ✓ done |
| Tasks    | 3/5 done |

Current task: <task-name>
Next step: <opsr:apply <change-name>
```

Then show:
- Recent activity (last 5 actions from episodic memory)
- Suggested next command based on current state
