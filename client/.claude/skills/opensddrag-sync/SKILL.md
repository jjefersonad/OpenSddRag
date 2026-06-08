# OpenSddRag — Sync
> Server: http://localhost:8000 | project_slug: `test-change`

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
