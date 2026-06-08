# OpenSddRag — Tasks
> Server: http://localhost:8000 | project_slug: `test-change`

Decomposes specs + design into atomic task artifacts, each < 4 hours.
Each task has: Goal, Acceptance criteria (referencing REQ-NNN), Dependencies.
Tasks are individual database artifacts — NOT a single markdown file.

**Run:** `/opsr:tasks <change-name>`

**Requires:** proposal + specs + design in database.
**Creates:** `<change-name>-task-<N>` artifacts in database.
**Unlocks:** /opsr:apply
