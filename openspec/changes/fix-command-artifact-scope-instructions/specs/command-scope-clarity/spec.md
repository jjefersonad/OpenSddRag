## ADDED Requirements

### Requirement: Artifact commands prohibit local file writes
SDD artifact-management commands (propose, spec, design, tasks, archive, explore, continue, status, search, sync) SHALL emit a header that explicitly prohibits creating local files or writing markdown to disk, restricting all data writes to the MCP server.

#### Scenario: Artifact command header restricts local writes
- **WHEN** a slash command for SDD artifact management is installed in a client project
- **THEN** its header MUST contain the statement that all reads and writes go through the MCP server and that local file creation is forbidden

#### Scenario: Artifact command header includes MCP server URL and project slug
- **WHEN** an artifact-management command is rendered via `opensddrag init`
- **THEN** the header MUST include the configured MCP server URL and the project slug

### Requirement: Implementation commands permit local file writes
Implementation-phase commands (apply, verify) SHALL emit a header that explicitly permits creating and editing local code files using standard file tools, while still directing SDD artifact reads and trace records through the MCP server.

#### Scenario: Apply command header allows local code writes
- **WHEN** the `/opsr:apply` slash command is installed in a client project
- **THEN** its header MUST NOT contain the phrase "DO NOT create local files"
- **THEN** its header MUST state that SDD artifacts are read from the MCP server and that code implementation uses local file tools (Edit, Write, Bash)

#### Scenario: Verify command header allows local reads
- **WHEN** the `/opsr:verify` slash command is installed in a client project
- **THEN** its header MUST permit reading local files when checking implementation evidence

### Requirement: Header distinction is encoded in template, not runtime
The two header variants SHALL be defined as named template functions in `client/src/templates/commands/index.js`, so the distinction is explicit, auditable, and not dependent on command-specific prose overriding a global restriction.

#### Scenario: Two distinct header functions exist
- **WHEN** reading `client/src/templates/commands/index.js`
- **THEN** there MUST be at least two distinct header-generating functions or constants: one for artifact-only scope and one for implementation scope

#### Scenario: Each command uses the correct header variant
- **WHEN** any command is rendered
- **THEN** artifact-management commands MUST use the artifact header
- **THEN** apply and verify MUST use the implementation header
