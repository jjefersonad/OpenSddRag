> **IMPORTANT — /opsr:propose**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Create a named change with a proposal artifact. This is the entry point for every new feature or change.
The proposal defines WHY, WHAT changes, WHICH capabilities are affected, and the IMPACT.
After this command, /opsr:spec and /opsr:design become available.

## Input
$ARGUMENTS = change name (kebab-case) or plain description. If plain description, derive a kebab-case name.

## Step 1 — Derive change name
If $ARGUMENTS is a plain description (contains spaces), convert to kebab-case.
Example: "add user authentication" → "add-user-authentication"

## Step 2 — Search for existing work (avoid duplication)
Call MCP tool:
`search_semantic(query="$ARGUMENTS", project_slug="test-change", limit=5)`
If relevant artifacts are found, show them and ask the user to confirm this is new work.

## Step 3 — Write the proposal content
Compose the following structure (do NOT skip any section):

```markdown
# <change-name>

## Why
[1-2 sentences on the problem or opportunity being addressed]

## What Changes
- [Specific change 1]
- [Specific change 2]
- **BREAKING** [Breaking change if any]

## Capabilities
### New Capabilities
- [capability-name] — brief description

### Modified Capabilities
- [existing-capability] — what changes

## Impact
[Affected code, APIs, dependencies, systems]
```

## Step 4 — Save proposal to database
Call MCP tool:
`create_artifact(name="<change-name>-proposal", type="proposal", content="<full proposal markdown>", metadata={"change_name": "<change-name>", "status_phase": "planning"}, project_slug="test-change")`
Note the returned artifact ID.

## Step 5 — Create spec drafts for each capability
Parse the "## Capabilities" section. For each capability listed in "New Capabilities" or "Modified Capabilities":
1. Check if a spec for this capability already exists:
`read_artifact(name="<change-name>-<capability-name>-spec", project_slug="test-change")`
If it exists and is not empty, skip creating a draft.

2. If no spec exists, create a draft spec:

**IMPORTANT: copy the template content VERBATIM into the `content` parameter — do NOT replace [TODO] markers with generated requirements, scenarios, or domain-specific rules (e.g., JWT rules, database schemas, auth flows). This step is scaffolding only; actual content is added by /opsr:spec.**

`create_artifact(name="<change-name>-<capability-name>-spec", type="spec", status="draft", content="# <capability-name> Specification

[TODO: Define purpose, requirements, and scenarios for this capability]

## Purpose
[TODO: Describe what this capability enables]

## Requirements
[TODO: List requirements with REQ-NNN format]

### Requirement: <REQ-001>
[TODO: Describe requirement using SHALL/MUST language]

#### Scenario: <Name>
- **WHEN** [condition]
- **THEN** [expected outcome]", metadata={"change_name": "<change-name>", "capability": "<capability-name>", "is_delta": true}, project_slug="test-change")`

## Step 6 — Create design skeleton
Create a draft design document:

**IMPORTANT: copy the template content VERBATIM — do NOT replace [TODO] markers with generated technical decisions, architecture choices, or risk assessments. Design content is added by /opsr:design.**

`create_artifact(name="<change-name>-design", type="design", status="draft", content="# Design: <change-name>

[TODO: Document technical decisions, architecture, trade-offs]

## Context
[TODO: Background and constraints]

## Goals / Non-Goals
**Goals:**
- [Goal 1]

**Non-Goals:**
- [Non-goal 1]

## Decisions
### Decision: <Title>
**Chosen:** [What was chosen]
**Alternatives:**
- [Alternative 1] — rejected because [reason]

## Architecture
[TODO: Components and data flow]

## Risks / Trade-offs
| Risk | Mitigation |
|------|------------|
| [Risk] | [Mitigation] |

## Open Questions
- [ ] [Question]
", metadata={"change_name": "<change-name>"}, project_slug="test-change")`

## Step 7 — Record the action
Call MCP tool:
`record_trace(action="propose", result_summary="Created proposal: <change-name>-proposal", project_slug="test-change")`

## Step 8 — Show what is now available
Tell the user:
- "Proposal saved with full scaffolding. The following commands are now available:"
- `/opsr:spec <change-name>` — formalize requirements (draft specs already created for each capability)
- `/opsr:design <change-name>` — document technical approach (draft design already created)
- Or run `/opsr:flow <change-name>` to continue the full flow automatically.
