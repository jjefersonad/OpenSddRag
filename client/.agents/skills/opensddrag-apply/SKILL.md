---
name: opensddrag-apply
description: Implement the next pending task against spec acceptance criteria
---

# OpenSddRag — Apply
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Implements tasks one at a time, reading ALL planning artifacts (proposal + specs + design) as context.
Marks tasks active → archived in the database after implementation.
Must validate each task against spec acceptance criteria before marking done.

**Run:** `/opsr:apply <change-name>`

**Requires:** all planning artifacts + pending tasks in database.
**Updates:** task status in database (draft → active → archived).
**After all tasks:** run /opsr:verify then /opsr:archive.
