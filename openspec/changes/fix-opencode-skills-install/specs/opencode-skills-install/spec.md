## ADDED Requirements

### Requirement: Init command installs OpenCode skills
The `opensddrag init` command SHALL install all 13 SDD skills to `.opencode/skills/<skill-name>/SKILL.md` when the user selects OpenCode as a configuration target.

#### Scenario: OpenCode selected in init prompt
- **WHEN** user runs `opensddrag init` and selects OpenCode from the tools prompt
- **THEN** the CLI SHALL create the directory `.opencode/skills/<skill-name>/` for each of the 13 SDD skills
- **AND** the CLI SHALL write a `SKILL.md` file in each directory with OpenCode-compatible format

#### Scenario: Skills installed to correct location
- **WHEN** OpenCode is selected during init
- **THEN** the system SHALL create skills at:
  - `.opencode/skills/opensddrag-propose/SKILL.md`
  - `.opencode/skills/opensddrag-spec/SKILL.md`
  - `.opencode/skills/opensddrag-design/SKILL.md`
  - `.opencode/skills/opensddrag-tasks/SKILL.md`
  - `.opencode/skills/opensddrag-apply/SKILL.md`
  - `.opencode/skills/opensddrag-verify/SKILL.md`
  - `.opencode/skills/opensddrag-sync/SKILL.md`
  - `.opencode/skills/opensddrag-archive/SKILL.md`
  - `.opencode/skills/opensddrag-explore/SKILL.md`
  - `.opencode/skills/opensddrag-continue/SKILL.md`
  - `.opencode/skills/opensddrag-status/SKILL.md`
  - `.opencode/skills/opensddrag-flow/SKILL.md`
  - `.opencode/skills/opensddrag-search/SKILL.md`

### Requirement: OpenCode skill files have required frontmatter
Each skill file installed to `.opencode/skills/` SHALL begin with YAML frontmatter containing:
- `name`: the skill identifier (kebab-case)
- `description`: brief description of the skill's purpose (1-1024 chars)
- `compatibility`: value MUST be `opencode`

#### Scenario: Frontmatter validates OpenCode format
- **WHEN** a skill file is created at `.opencode/skills/<name>/SKILL.md`
- **THEN** the file SHALL start with YAML frontmatter matching:
  ```yaml
  ---
  name: opensddrag-<skill>
  description: <description text>
  compatibility: opencode
  ---
  ```

### Requirement: Skill description extracted from template
The skill description in frontmatter SHALL be derived from the skill's template content by extracting the first paragraph after the skill title.

#### Scenario: Description extracted from skill content
- **WHEN** an OpenCode skill file is generated
- **THEN** the `description` field SHALL contain text extracted from the skill's purpose description (first substantial paragraph)
- **AND** the description SHALL be between 1 and 1024 characters

### Requirement: Dual installation for multi-tool users
The CLI SHALL install skills to both Claude Code paths (`.claude/skills/`, `.agents/skills/`) AND OpenCode path (`.opencode/skills/`) when OpenCode is selected.

#### Scenario: Skills available in all supported locations
- **WHEN** OpenCode is selected during init
- **THEN** skills SHALL be installed to:
  - `.claude/skills/opensddrag-<skill>/SKILL.md`
  - `.agents/skills/opensddrag-<skill>/SKILL.md`
  - `.opencode/skills/opensddrag-<skill>/SKILL.md`

### Requirement: Init command creates MCP config for OpenCode
The `opensddrag init` command SHALL write OpenCode MCP configuration to `opencode.json` with the correct format.

#### Scenario: OpenCode MCP config created
- **WHEN** OpenCode is selected during init
- **THEN** the CLI SHALL update `opencode.json` with:
  ```json
  {
    "mcp": {
      "opensddrag": {
        "type": "remote",
        "url": "<server-url>/sse",
        "enabled": true
      }
    }
  }
  ```

### Requirement: Init output reports OpenCode skill installation
The CLI SHALL display confirmation of OpenCode skill installation in its output summary.

#### Scenario: Installation summary includes OpenCode skills
- **WHEN** `opensddrag init` completes with OpenCode selected
- **THEN** the output SHALL include lines showing:
  - MCP configuration file created/updated
  - Skills installed to `.opencode/skills/` with count