---
name: opensddrag-design
description: Document technical decisions, architecture, and trade-offs for a change
---

# OpenSddRag — Design
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Creates a design document: Context, Goals, Decisions (with alternatives), Architecture, Risks, Migration.
Must read proposal and all specs from the database as context.

**Run:** `/opsr:design <change-name>`

**Requires:** proposal + specs in database.
**Creates:** `<change-name>-design` artifact in database.
**Unlocks:** /opsr:tasks
