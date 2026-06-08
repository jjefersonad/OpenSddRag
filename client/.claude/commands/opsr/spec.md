> **IMPORTANT — /opsr:spec**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Create one or more spec artifacts for the capabilities listed in a proposal.
Each capability in "New Capabilities" or "Modified Capabilities" gets its own spec artifact.
Specs use SHALL/MUST language and must have Scenarios with WHEN/THAN format.

## Input
$ARGUMENTS = change name. If not provided, list proposals and ask.

## Step 1 — Read the proposal from the database
Call MCP tool:
`list_artifacts(type="proposal", project_slug="test-change")`
Then read the selected proposal:
`read_artifact(name="<change-name>-proposal", project_slug="test-change")`

## Step 2 — Identify capabilities from the proposal
Parse the "## Capabilities" section. Each capability in "New Capabilities" and "Modified Capabilities" needs a spec.

**New capability** → create a full spec (Purpose + Requirements + Scenarios)
**Modified capability** → check if a main spec exists first:
`search_semantic(query="<capability-name> spec", project_slug="test-change", limit=3)`
If main spec exists → create a DELTA spec with ADDED/MODIFIED/REMOVED/RENAMED sections.
If no main spec → create BOTH:
1. The main spec with metadata={"capability": "<capability-name>", "is_delta": false}
2. The delta spec with metadata={"change_name": "<change-name>", "capability": "<capability-name>", "is_delta": true}

## Step 3 — Write spec content for EACH capability

### Full spec structure (new capabilities):
```markdown
# <capability-name> Specification

## Purpose
[High-level description of this capability]

## Requirements

### Requirement: <REQ-001 Name>
[Description using SHALL/MUST language]

#### Scenario: <Happy path name>
- **WHEN** [condition]
- **THEN** [expected outcome]

#### Scenario: <Edge case name>
- **WHEN** [edge condition]
- **THEN** [expected outcome]

### Requirement: <REQ-002 Name>
[Description]

#### Scenario: <Name>
- **WHEN** [condition]
- **THEN** [outcome]
```

### Delta spec structure (modified capabilities):
```markdown
# <capability-name> Specification — Delta

## ADDED Requirements
### Requirement: <New requirement name>
[Full requirement with scenarios]

## MODIFIED Requirements
### Requirement: <Existing requirement name>
[Updated requirement — include FULL updated text with all scenarios]

## REMOVED Requirements
### Requirement: <Removed requirement name>
**Reason:** [Why this is being removed]
**Migration:** [How consumers should migrate]

## RENAMED Requirements
- FROM: `### Requirement: Old Name`
- TO: `### Requirement: New Name`
```

## Step 4 — Save each spec to the database
For each capability spec:
`create_artifact(name="<change-name>-<capability-name>-spec", type="spec", content="<full spec markdown>", metadata={"change_name": "<change-name>", "capability": "<capability-name>", "is_delta": true/false}, project_slug="test-change")`

## Step 5 — Link each spec to the proposal
`link_artifacts(source_name="<spec-name>", target_name="<change-name>-proposal", relationship_type="implements", project_slug="test-change")`

## Step 6 — Validate each spec
`validate_artifact(name="<spec-name>", project_slug="test-change")`
Fix any validation errors before continuing.

## Step 7 — Record the action
`record_trace(action="spec", result_summary="Created specs for: <capability-list>", project_slug="test-change")`

## Step 8 — Show what is now available
- "Specs saved. You can now run:"
- `/opsr:design <change-name>` — document technical decisions
