> **IMPORTANT — /opsr:verify**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Validate the implementation against the spec requirements and design decisions.
Produces a structured report with CRITICAL, WARNING, and SUGGESTION severity levels.
Does NOT modify any artifacts — read-only operation.

## Input
$ARGUMENTS = change name.

## Step 1 — Load all artifacts from the database
`read_artifact(name="<change-name>-proposal", project_slug="test-change")`
`read_artifact(name="<change-name>-design", project_slug="test-change")`
Get all specs and tasks for this change:
`get_relationships(name="<change-name>-proposal", project_slug="test-change")`
Read each linked spec and task artifact.

## Step 2 — Verify COMPLETENESS
Check task completion:
`list_artifacts(type="task", status="draft", project_slug="test-change")`
- If pending tasks exist → **CRITICAL: Tasks not complete**

Extract all requirements (REQ-NNN) from specs.
For each requirement, search the codebase for implementation evidence.
- If requirement has no implementation evidence → **CRITICAL: Requirement not implemented**

## Step 3 — Verify CORRECTNESS
For each spec scenario (WHEN/THAN blocks):
- Search the codebase for test coverage or implementation of the scenario condition
- If scenario has no coverage → **WARNING: Scenario not covered**

## Step 4 — Verify COHERENCE
Extract decisions from the "## Decisions" section of the design.
For each decision:
- Check if the implementation follows the chosen approach
- If implementation deviates from a decision → **SUGGESTION: Possible deviation from design**

## Step 5 — Generate report
Output a structured report:

```
## Verification Report: <change-name>

### Summary
| Dimension    | Status |
|--------------|--------|
| Completeness | ✓/✗   |
| Correctness  | ✓/✗   |
| Coherence    | ✓/✗   |

### CRITICAL Issues
- [Issue description]

### WARNING Issues
- [Issue description]

### SUGGESTIONS
- [Issue description]

### Assessment
[READY TO ARCHIVE | ISSUES MUST BE FIXED BEFORE ARCHIVING]
```

## Step 6 — Record the verification
`record_trace(action="verify", result_summary="Verification: <PASS/FAIL> — <N> critical, <N> warnings", project_slug="test-change")`
