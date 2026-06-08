# OpenSddRag — Spec
> Server: http://localhost:8000 | project_slug: `test-change`

Creates spec artifacts for each capability listed in the proposal.
Uses SHALL/MUST language. Each requirement MUST have Scenarios with WHEN/THEN format.

**New capability** → full spec (Purpose + Requirements + Scenarios)
**Modified capability** → delta spec (ADDED / MODIFIED / REMOVED / RENAMED sections)

**Run:** `/opsr:spec <change-name>`

**Requires:** proposal artifact in database.
**Creates:** `<change-name>-<capability>-spec` artifact(s) in database.
**Unlocks:** /opsr:design (when all capabilities have specs)
