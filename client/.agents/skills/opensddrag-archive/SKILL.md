---
name: opensddrag-archive
description: Finalize a completed change by archiving all its artifacts
---

# OpenSddRag — Archive
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Finalizes a completed change: validates, syncs delta specs, archives all artifacts.

Steps:
1. Validate artifact and task completion (warns if incomplete)
2. Sync delta specs to main specs (if any)
3. Mark all change artifacts as archived in database

**Run:** `/opsr:archive <change-name>`

**Requires:** all tasks completed (or user confirmation to archive anyway).
**Updates:** all change artifacts to status=archived in database.
