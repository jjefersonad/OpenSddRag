---
name: opensddrag-flow
description: Run the complete SDD flow end-to-end in one session
---

# OpenSddRag — Flow
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Runs the complete SDD flow end-to-end: propose → spec → design → tasks → apply → archive.
ALL artifacts saved to database via MCP — no local files created.

Use when: implementing a feature from scratch in a single session.

**Run:** `/opsr:flow <feature description>`
