> **IMPORTANT — /opsr:flow**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Run the complete SDD flow end-to-end in a single session.
ALL artifacts are saved to the database via MCP tools — no local files.

## Input
$ARGUMENTS = feature description or change name.

## PHASE 1 — Propose
Follow <opsr:propose steps:
1. `search_semantic(query="$ARGUMENTS", project_slug="test-change")` — check for duplicates
2. Compose proposal content (Why / What Changes / Capabilities / Impact)
3. `create_artifact(name="<change-name>-proposal", type="proposal", content="...", project_slug="test-change")`

## PHASE 2 — Spec
Follow /opsr:spec steps for each capability in the proposal:
4. For each capability: compose spec (Purpose / Requirements with SHALL / Scenarios with WHEN-THAN)
5. `create_artifact(name="<change-name>-<capability>-spec", type="spec", content="...", project_slug="test-change")`
6. `link_artifacts(source_name="<spec>", target_name="<proposal>", relationship_type="implements", project_slug="test-change")`
7. `validate_artifact(name="<spec>", project_slug="test-change")` — fix errors before continuing

## PHASE 3 — Design
Follow /opsr:design steps:
8. Read all specs just created
9. Compose design (Context / Goals / Decisions / Architecture / Risks / Migration)
10. `create_artifact(name="<change-name>-design", type="design", content="...", project_slug="test-change")`
11. `link_artifacts(source_name="<design>", target_name="<proposal>", relationship_type="depends_on", project_slug="test-change")`

## PHASE 4 — Tasks
Follow <opsr:tasks steps:
12. Read proposal, all specs, and design from database
13. For each task: `create_artifact(name="<change-name>-task-<N>", type="task", content="...", project_slug="test-change")`
14. `link_artifacts(source_name="<task>", target_name="<spec>", relationship_type="implements", project_slug="test-change")`

## PHASE 5 — Apply (repeat for each task in order)
Follow <opsr:apply steps:
15. Read ALL planning artifacts as context (proposal + specs + design)
16. `update_artifact(name="<task>", status="active", project_slug="test-change")`
17. Implement the task against its acceptance criteria
18. `update_artifact(name="<task>", status="archived", project_slug="test-change")`
19. `record_trace(action="apply_task", result_summary="Completed: <task>", project_slug="test-change")`

## PHASE 6 — Archive
Follow <opsr:archive steps:
20. Sync delta specs if any
21. `update_artifact(name="<all artifacts>", status="archived", project_slug="test-change")`
22. `record_trace(action="complete_flow", result_summary="Completed: $ARGUMENTS", project_slug="test-change")`
