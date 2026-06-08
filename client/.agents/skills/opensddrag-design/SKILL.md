# OpenSddRag — Design
> Server: http://localhost:8000 | project_slug: `test-change`

Creates a design document: Context, Goals, Decisions (with alternatives), Architecture, Risks, Migration.
Must read proposal and all specs from the database as context.

**Run:** `/opsr:design <change-name>`

**Requires:** proposal + specs in database.
**Creates:** `<change-name>-design` artifact in database.
**Unlocks:** /opsr:tasks
