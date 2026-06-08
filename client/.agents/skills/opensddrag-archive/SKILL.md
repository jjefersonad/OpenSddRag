# OpenSddRag — Archive
> Server: http://localhost:8000 | project_slug: `test-change`

Finalizes a completed change: validates, syncs delta specs, archives all artifacts.

Steps:
1. Validate artifact and task completion (warns if incomplete)
2. Sync delta specs to main specs (if any)
3. Mark all change artifacts as archived in database

**Run:** `/opsr:archive <change-name>`

**Requires:** all tasks completed (or user confirmation to archive anyway).
**Updates:** all change artifacts to status=archived in database.
