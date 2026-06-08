## Why

When users run `opensddrag init` and select OpenCode, the CLI writes slash commands to `.claude/commands/opsr/` in Claude Code format. However, OpenCode uses a **different command format and location**:

- **Claude Code**: `.claude/commands/opsr/<command>.md` with special `/opsr:` prefix
- **OpenCode**: `.opencode/commands/<command>.md` with YAML frontmatter (description, agent, model)

Currently, OpenCode users receive NO slash commands because the Claude Code format is incompatible with OpenCode's native command system.

## What Changes

1. **Create OpenCode-specific command templates** in `client/src/templates/commands/opencode.js`
2. **Modify `init.js`** to install commands to `.opencode/commands/` when OpenCode is selected
3. **Convert Claude Code format to OpenCode format**:
   - Rename: `propose.md` → `propose` (filename = command name)
   - Add YAML frontmatter: `description`, `agent`, `model`
   - Remove `/opsr:` prefixes from content
   - Add `---` delimiters around content

## Capabilities

### New Capabilities
- `opencode-commands-install`: Install OpenCode-native command files with proper frontmatter and directory structure

### Modified Capabilities
- `client-init-command`: Modify init command to support OpenCode command installation (currently only installs Claude Code commands)

## Impact

- **New file**: `client/src/templates/commands/opencode.js` (OpenCode command templates)
- **Modified file**: `client/src/commands/init.js` (add OpenCode command installation)
- **No new dependencies**: Uses existing command template structure
- **Backward compatible**: Claude Code commands continue to work unchanged