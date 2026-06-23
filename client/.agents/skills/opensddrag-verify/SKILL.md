---
name: opensddrag-verify
description: Validate implementation against spec requirements and design decisions
---

# OpenSddRag — Verify
> **MCP server:** `opensddrag` (http://localhost:8000) | **project_slug:** `opensddrag`
> **Available tools:** `create_artifact`, `read_artifact`, `list_artifacts`, `update_artifact`, `validate_artifact`, `link_artifacts`, `get_relationships`, `search_semantic`, `recall_episodes`, `get_working_context`, `update_working_context`, `record_trace`
> If these tools are not in your active tool list, the `opensddrag` MCP server is not connected — STOP and inform the user.

Read-only validation of the implementation against spec requirements and design decisions.
Produces a report with CRITICAL / WARNING / SUGGESTION severity levels.

Checks:
- **Completeness**: all tasks done, all REQ-NNN implemented
- **Correctness**: all spec scenarios covered
- **Coherence**: implementation follows design decisions

**Run:** `/opsr:verify <change-name>`

**Requires:** all artifacts in database + implementation in codebase.
**Output:** verification report (no artifacts modified).
