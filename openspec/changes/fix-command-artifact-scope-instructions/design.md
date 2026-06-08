## Context

The client-side slash commands are generated from a single JavaScript module (`client/src/templates/commands/index.js`). A shared `header(name)` function produces a preamble that is prepended verbatim to every command's markdown. The preamble contains three blanket restrictions:
1. All reads/writes through the MCP server
2. Do NOT create local files
3. Do NOT write markdown to disk

This is correct for the SDD artifact phase (proposals, specs, designs, tasks), where everything must be stored in the database so it can be semantically searched and recalled across sessions. But `/opsr:apply` invokes these restrictions while simultaneously instructing Claude to "implement the code changes" — a contradiction that either breaks implementation or confuses the model.

## Goals / Non-Goals

**Goals:**
- Eliminate the contradiction between the global "no local files" header and the implementation instruction in `/opsr:apply` and `/opsr:verify`
- Make the distinction between SDD artifact writes and code implementation writes explicit and impossible to miss
- Require zero changes to the MCP server, database, or client-project runtime behavior

**Non-Goals:**
- Changing what the MCP tools do or the data they store
- Modifying how `opensddrag init` installs commands (install process is unchanged)
- Altering command _logic_ — only the headers are being changed

## Decisions

### Decision 1: Two named header functions, not one

**Choice**: Replace the single `header(name)` with two functions:
- `artifactHeader(name)` — the existing restriction verbatim ("DO NOT create local files")
- `implementHeader(name)` — permits local file I/O; clarifies that the MCP server is used only for reading SDD artifacts and recording traces

**Alternatives considered**:
- *Single header with a note*: Add "except during apply" to the existing header. Rejected — a parenthetical override of a blanket rule is fragile and easy to miss; future authors may rewrite the note while keeping the restriction.
- *No header in apply*: Drop the header from apply entirely. Rejected — the apply command still reads from the MCP server and records traces; losing the header removes the MCP URL and project slug reminder.
- *Runtime check inside header*: Pass a flag `header(name, allowLocalFiles)`. Viable but less readable than two named functions.

### Decision 2: Flow command gets the artifact header

The `/opsr:flow` command covers the full SDD lifecycle in one shot. Its planning phase (propose → spec → design → tasks) is artifact-only; the implementation phase mirrors apply. Rather than splitting flow, we apply `artifactHeader` and add an inline note within the flow command's implementation section clarifying that code writes are allowed there. This keeps flow as a single command without a hybrid header.

### Decision 3: No changes to command content beyond headers

Only the header strings change. The body of each command (steps, tool calls, logic) is unchanged. This minimizes diff surface and avoids introducing new bugs in command logic.

## Risks / Trade-offs

- [Risk] Future developers add a new command and copy the wrong header → Mitigation: add a JSDoc comment above each function documenting which commands use it and why
- [Risk] The `implementHeader` is worded in a way that still confuses models → Mitigation: use affirmative phrasing ("code changes are written locally using Edit/Write/Bash tools") rather than a list of exceptions to the old rule

## Migration Plan

1. Edit `client/src/templates/commands/index.js`: add `implementHeader(name)` alongside existing `header(name)` (which becomes `artifactHeader(name)`)
2. Update each command to call the appropriate header function
3. Re-run `opensddrag init` in any client project to regenerate the installed command files — existing installs keep the old headers until refreshed (non-breaking; old behavior was just contradictory, not harmful)

No database migrations, no version bumps to the MCP protocol, no breaking API changes.

## Open Questions

- Should `artifactHeader` be renamed from the current `header` with a deprecation path, or simply replaced in-place? Leaning toward in-place replacement since this is an internal module with no external consumers.
