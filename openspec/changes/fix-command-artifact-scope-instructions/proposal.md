## Why

The slash command templates installed by `opensddrag init` prepend a header to every command declaring "DO NOT create local files" — but `/opsr:apply` explicitly asks Claude to implement code changes, which requires writing local files. This contradiction causes Claude to either refuse implementation or misapply the restriction, undermining the core purpose of the apply phase.

## What Changes

- Split the shared `header()` into two variants: one for SDD artifact commands (no local files) and one for implementation commands (local file writes allowed and expected)
- The apply, verify, and flow commands use the implementation-aware header that clarifies: SDD artifacts go to MCP; code implementation uses standard file tools
- The prohibition "DO NOT create local files" is scoped to SDD planning artifacts (proposal, spec, design, tasks markdown) not to code implementation files

## Capabilities

### New Capabilities

- `command-scope-clarity`: Separate header templates for SDD-artifact commands vs. implementation commands, with explicit language distinguishing where each type of write goes

### Modified Capabilities

<!-- No existing specs — this is the first tracked change -->

## Impact

- `client/src/templates/commands/index.js`: Refactor `header()` into `artifactHeader()` and `implementHeader()`; apply the correct variant to each command
- Commands that get `artifactHeader()`: `propose`, `spec`, `design`, `tasks`, `archive`, `explore`, `continue`, `status`, `flow` (planning phase only), `search`, `sync`
- Commands that get `implementHeader()`: `apply`, `verify`; `flow` gets both depending on phase
- No database changes, no MCP protocol changes, no client/server API changes
