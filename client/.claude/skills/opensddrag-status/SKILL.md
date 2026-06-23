---
name: opensddrag-status
description: Show current state of all in-progress changes
---

# OpenSddRag — Status
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Shows current state of all in-progress changes: artifact completion, task progress, recent activity.

Reads from MCP server — no local files.

**Run:** `/opsr:status` or `/opsr:status <change-name>`
