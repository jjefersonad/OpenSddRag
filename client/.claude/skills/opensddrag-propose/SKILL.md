---
name: opensddrag-propose
description: Create a named change proposal — entry point for every feature or bugfix
---

# OpenSddRag — Propose
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Creates a named **change** with a proposal artifact: Why, What Changes, Capabilities, Impact.
Entry point for every new feature or bugfix. No code is written here.
After this, /opsr:spec and /opsr:design become available.

**Run:** `/opsr:propose <change-name or description>`

**Creates:** `<change-name>-proposal` artifact in database.
**Unlocks:** /opsr:spec, /opsr:design
