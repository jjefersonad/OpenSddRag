## Why

When users run `opensddrag init` and select OpenCode as a target, the CLI only configures the MCP connection in `opencode.json` but **fails to install any skills**. OpenCode requires skills to be installed in `.opencode/skills/<name>/SKILL.md` with specific frontmatter including `compatibility: opencode`. Currently, skills are only written to `.claude/skills/` and `.agents/skills/`, which are Claude Code paths and incompatible with OpenCode's native skill format.

This bug leaves OpenCode users without access to the 13 SDD skills (propose, spec, design, tasks, apply, verify, sync, archive, explore, continue, status, flow, search) that Claude Code users receive.

## What Changes

1. **Modify `init.js`** to create `.opencode/skills/` directory structure when OpenCode is selected
2. **Install all 13 SDD skills** to `.opencode/skills/<skill-name>/SKILL.md` with OpenCode-compatible frontmatter
3. **Add `compatibility: opencode`** to each skill's frontmatter YAML
4. **Ensure dual installation**: Continue installing to `.claude/skills/` and `.agents/skills/` for Claude Code compatibility, plus `.opencode/skills/` for OpenCode

## Capabilities

### New Capabilities
- `opencode-skills-install`: Install OpenCode-native skill files with proper frontmatter and directory structure

### Modified Capabilities
- `client-init-command`: Modify the init command to support OpenCode skill installation (currently only installs MCP config)

## Impact

- **Modified file**: `client/src/commands/init.js`
- **No new dependencies**: Uses existing skill template functions
- **Backward compatible**: Claude Code installation continues to work unchanged
- **Configuration**: OpenCode users gain access to all SDD skills via native OpenCode skill system