## ADDED Requirements

### Requirement: Project documentation is written in English
All project-level text artifacts — README files, inline source-code comments, SQL migration comments, documentation pages under `docs/`, and CLI help strings — SHALL be written in English.

#### Scenario: README is readable in English
- **WHEN** a developer opens `README.md` at the repository root
- **THEN** all prose, headings, and table content MUST be in English with no Portuguese phrases

#### Scenario: SQL migration file uses English comments
- **WHEN** a developer reads any file under `mcp-server/src/opensddrag/db/migrations/`
- **THEN** all SQL block comments and inline comments MUST be in English

#### Scenario: Documentation pages are in English
- **WHEN** a developer reads any file under `docs/`
- **THEN** all content MUST be in English

### Requirement: Runtime user-generated content is language-agnostic
Artifacts stored in the database at runtime (proposals, specs, designs, tasks, skills, execution traces, and session context) SHALL be stored exactly as the user writes them, regardless of language.

#### Scenario: User creates an artifact in Portuguese
- **WHEN** an agent stores a proposal, spec, task, skill, or trace written in Portuguese via any MCP tool
- **THEN** the database record MUST preserve the original Portuguese text without modification or translation

#### Scenario: User creates an artifact in any language
- **WHEN** an agent stores content in any human language via the MCP tools
- **THEN** the system MUST accept and persist the content as-is

### Requirement: No language-enforcement gate in the MCP server
The MCP server SHALL NOT validate or reject stored content based on detected language; language policy is a developer convention, not a runtime constraint.

#### Scenario: MCP tool receives non-English content
- **WHEN** a `create_artifact`, `update_artifact`, or `log_trace` MCP tool call is made with non-English text in any field
- **THEN** the server MUST accept the request and store the content without returning a language-related error
