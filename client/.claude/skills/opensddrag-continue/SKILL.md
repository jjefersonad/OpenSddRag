---
name: opensddrag-continue
description: Create the next single artifact in the SDD dependency chain
---

# OpenSddRag — Continue
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Creates the NEXT SINGLE artifact in the dependency chain and stops.
Unlike /opsr:flow, creates one artifact per invocation.

Dependency order: proposal → specs → design → tasks

Use when: stepping through the SDD flow one artifact at a time.

**Run:** `/opsr:continue <change-name>`
