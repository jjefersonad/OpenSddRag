## ADDED Requirements

### Requirement: Quick-install documentation in README.md
The project README.md SHALL contain a dedicated "Quick Install (Client Only)" section that guides a user from zero to a configured local client in a single reading, targeting developers who only need to connect to an already-running hosted MCP server.

#### Scenario: User finds setup instructions without reading the full README
- **WHEN** a user opens README.md looking for "how to connect to the hosted server"
- **THEN** they SHALL find a clearly labelled section (e.g., "Quick Install" or "Conectando ao Servidor Hospedado") near the top that lists the exact commands to install and configure the client

#### Scenario: All commands in the section are copy-pasteable
- **WHEN** a user copies any code block from the Quick Install section
- **THEN** running it SHALL either succeed directly or produce a clear error message explaining what is missing

### Requirement: Client CLI provides actionable success output after init
The `opensddrag init` command SHALL print a summary after successful setup listing: the MCP server URL configured, the project slug used, and the next steps (e.g., "open your project in Claude Code").

#### Scenario: Successful init prints confirmation
- **WHEN** `node bin/opensddrag.js init --server <url> --project <slug>` completes without error
- **THEN** the output SHALL include the configured server URL, the project slug, and at least one "what to do next" hint

#### Scenario: Missing required flag produces helpful error
- **WHEN** the user runs `opensddrag init` without `--server` or without `--project`
- **THEN** the CLI SHALL print an error message that names the missing flag and shows the correct usage example

### Requirement: client/README.md documents the end-user setup flow
The `client/` package SHALL contain (or update) a `README.md` that focuses exclusively on the end-user client setup scenario: prerequisites, install command, init command with flags, and verification step.

#### Scenario: Standalone client README is self-contained
- **WHEN** a user reads only `client/README.md`
- **THEN** they SHALL have everything needed to install the client and connect it to the hosted server without needing to read the root README.md
