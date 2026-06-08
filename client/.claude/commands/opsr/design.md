> **IMPORTANT — /opsr:design**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Create a design document that captures technical decisions, architecture, trade-offs, and open questions.
The design must be based on the proposal and spec artifacts already in the database.

## Input
$ARGUMENTS = change name.

## Step 1 — Read proposal and all specs from the database
`read_artifact(name="<change-name>-proposal", project_slug="test-change")`
`list_artifacts(type="spec", project_slug="test-change")`
Read each spec linked to this change:
`get_relationships(name="<change-name>-proposal", project_slug="test-change")`

## Step 2 — Search for related prior designs
`search_semantic(query="<change topic> design decisions", project_slug="test-change", limit=3)`
Use findings as context — don't duplicate prior work.

## Step 3 — Write the design content
```markdown
# Design: <change-name>

## Context
[Background, current state, constraints that shaped this design]

## Goals / Non-Goals
**Goals:**
- [What this design achieves]

**Non-Goals:**
- [What this design deliberately does NOT address]

## Decisions

### Decision: <Title>
**Chosen:** [What was chosen and why]
**Alternatives considered:**
- [Alternative 1] — rejected because [reason]
- [Alternative 2] — rejected because [reason]

### Decision: <Title>
...

## Architecture
[Components, data flow, integration points — use ASCII diagrams if helpful]

## Risks / Trade-offs
| Risk | Mitigation |
|------|------------|
| [Risk] | [Mitigation] |

## Migration Plan
[Deployment steps, backward compatibility, rollback plan]

## Open Questions
- [ ] [Question that still needs resolution]
```

## Step 4 — Save design to database
`create_artifact(name="<change-name>-design", type="design", content="<full design markdown>", metadata={"change_name": "<change-name>"}, project_slug="test-change")`

## Step 5 — Link design to proposal
`link_artifacts(source_name="<change-name>-design", target_name="<change-name>-proposal", relationship_type="depends_on", project_slug="test-change")`

## Step 6 — Record and show next steps
`record_trace(action="design", result_summary="Created design: <change-name>-design", project_slug="test-change")`
Tell the user: "Design saved. Run `<opsr:tasks <change-name>` to decompose into tasks."
