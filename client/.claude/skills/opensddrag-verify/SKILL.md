# OpenSddRag — Verify
> Server: http://localhost:8000 | project_slug: `test-change`

Read-only validation of the implementation against spec requirements and design decisions.
Produces a report with CRITICAL / WARNING / SUGGESTION severity levels.

Checks:
- **Completeness**: all tasks done, all REQ-NNN implemented
- **Correctness**: all spec scenarios covered
- **Coherence**: implementation follows design decisions

**Run:** `/opsr:verify <change-name>`

**Requires:** all artifacts in database + implementation in codebase.
**Output:** verification report (no artifacts modified).
