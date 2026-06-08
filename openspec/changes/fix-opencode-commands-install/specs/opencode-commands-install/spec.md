## ADDED Requirements

### Requirement: Init command installs OpenCode commands
The `opensddrag init` command SHALL install all 13 SDD commands to `.opencode/commands/<name>.md` when the user selects OpenCode as a configuration target.

#### Scenario: OpenCode selected in init prompt
- **WHEN** user runs `opensddrag init` and selects OpenCode from the tools prompt
- **THEN** the CLI SHALL create the directory `.opencode/commands/`
- **AND** the CLI SHALL write a `<command>.md` file for each of the 13 SDD commands

#### Scenario: Commands installed to correct location
- **WHEN** OpenCode is selected during init
- **THEN** the system SHALL create commands at:
  - `.opencode/commands/propose.md`
  - `.opencode/commands/spec.md`
  - `.opencode/commands/design.md`
  - `.opencode/commands/tasks.md`
  - `.opencode/commands/apply.md`
  - `.opencode/commands/verify.md`
  - `.opencode/commands/sync.md`
  - `.opencode/commands/archive.md`
  - `.opencode/commands/explore.md`
  - `.opencode/commands/continue.md`
  - `.opencode/commands/status.md`
  - `.opencode/commands/flow.md`
  - `.opencode/commands/search.md`

### Requirement: OpenCode command files have required frontmatter
Each command file installed to `.opencode/commands/` SHALL begin with YAML frontmatter containing:
- `description`: brief description of the command's purpose (1-1024 chars)
- Optionally `agent`: the agent type to use (e.g., "plan", "build")
- Optionally `model`: the specific model to use

#### Scenario: Frontmatter validates OpenCode format
- **WHEN** a command file is created at `.opencode/commands/<name>.md`
- **THEN** the file SHALL start with YAML frontmatter matching:
  ```yaml
  ---
  description: <description text>
  agent: <agent-name>
  model: <model-identifier>
  ---
  <prompt content>
  ```
- **AND** the frontmatter SHALL be delimited by `---` lines

### Requirement: Command content removes opsr: prefix references
The prompt content in OpenCode command files SHALL remove all `/opsr:` prefix references and adapt them to OpenCode's direct command invocation format.

#### Scenario: Content converted from Claude Code format
- **WHEN** a Claude Code command is converted to OpenCode format
- **THEN** all references to `/opsr:<command>` SHALL be converted to `/<command>`
- **AND** all references to `$ARGUMENTS = /opsr:<command>` SHALL be converted to `$ARGUMENTS = /<command>`
- **AND** the actual prompt logic and steps SHALL remain unchanged

### Requirement: Init output reports OpenCode command installation
The CLI SHALL display confirmation of OpenCode command installation in its output summary.

#### Scenario: Installation summary includes OpenCode commands
- **WHEN** `opensddrag init` completes with OpenCode selected
- **THEN** the output SHALL include lines showing:
  - Command files created in `.opencode/commands/`
  - Count of commands installed

### Requirement: Dual command installation for multi-tool users
The CLI SHALL install commands to both Claude Code paths (`.claude/commands/opsr/`) AND OpenCode path (`.opencode/commands/`) when OpenCode is selected.

#### Scenario: Commands available in all supported locations
- **WHEN** OpenCode is selected during init
- **THEN** commands SHALL be installed to:
  - `.claude/commands/opsr/<name>.md` (Claude Code format)
  - `.opencode/commands/<name>.md` (OpenCode format)