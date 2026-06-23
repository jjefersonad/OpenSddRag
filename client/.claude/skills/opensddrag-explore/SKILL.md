---
name: opensddrag-explore
description: Investigate a problem or idea without writing any code
---

# OpenSddRag — Explore
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Thinking mode — investigates ideas WITHOUT implementing any code.
Reads existing specs and codebase for context. Can create artifacts to capture insights.

Rules:
- NEVER write application code
- NEVER create implementation files
- MAY create/update OpenSddRag artifacts to capture decisions

Use when: thinking through options, investigating feasibility, comparing approaches.
Transition: when ready → /opsr:propose <name>

**Run:** `/opsr:explore <topic or question>`
