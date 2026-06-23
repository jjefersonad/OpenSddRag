---
name: opensddrag-spec
description: Write capability specs with SHALL/MUST requirements and WHEN/THEN scenarios
---

# OpenSddRag — Spec
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Creates spec artifacts for each capability listed in the proposal.
Uses SHALL/MUST language. Each requirement MUST have Scenarios with WHEN/THEN format.

**New capability** → full spec (Purpose + Requirements + Scenarios)
**Modified capability** → delta spec (ADDED / MODIFIED / REMOVED / RENAMED sections)

**Run:** `/opsr:spec <change-name>`

**Requires:** proposal artifact in database.
**Creates:** `<change-name>-<capability>-spec` artifact(s) in database.
**Unlocks:** /opsr:design (when all capabilities have specs)
