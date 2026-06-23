---
name: opensddrag-sync
description: Merge delta specs back into main capability specs
---

# OpenSddRag — Sync
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Merges delta specs (ADDED/MODIFIED/REMOVED/RENAMED) into main specs stored in the database.
Called automatically during /opsr:archive when delta specs exist.

Delta operations:
- **ADDED** → append new requirement to main spec
- **MODIFIED** → apply partial updates (not wholesale replace)
- **REMOVED** → delete requirement + add Reason/Migration note
- **RENAMED** → rename requirement heading

**Run:** `/opsr:sync <change-name>`

**Requires:** delta specs + main specs in database.
**Updates:** main spec artifacts in database.
