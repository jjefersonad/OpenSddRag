---
name: opensddrag-tasks
description: Break a design into atomic, verifiable implementation tasks
---

# OpenSddRag — Tasks
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Decomposes specs + design into atomic task artifacts, each < 4 hours.
Each task has: Goal, Acceptance criteria (referencing REQ-NNN), Dependencies.
Tasks are individual database artifacts — NOT a single markdown file.

**Run:** `/opsr:tasks <change-name>`

**Requires:** proposal + specs + design in database.
**Creates:** `<change-name>-task-<N>` artifacts in database.
**Unlocks:** /opsr:apply
