# OpenSddRag — Apply
> Server: http://localhost:8000 | project_slug: `test-change`

Implements tasks one at a time, reading ALL planning artifacts (proposal + specs + design) as context.
Marks tasks active → archived in the database after implementation.
Must validate each task against spec acceptance criteria before marking done.

**Run:** `/opsr:apply <change-name>`

**Requires:** all planning artifacts + pending tasks in database.
**Updates:** task status in database (draft → active → archived).
**After all tasks:** run /opsr:verify then /opsr:archive.
