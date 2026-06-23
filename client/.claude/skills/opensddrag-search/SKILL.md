---
name: opensddrag-search
description: Semantic search over specs, tasks, and past agent actions
---

# OpenSddRag — Search
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Semantic search over the SDD knowledge base using pgvector similarity.
Always run this BEFORE starting new work to find existing specs and decisions.

Searches: this project first, then all projects if no results.
Also recalls past agent actions (episodic memory).

**Run:** `/opsr:search <natural language query>`
