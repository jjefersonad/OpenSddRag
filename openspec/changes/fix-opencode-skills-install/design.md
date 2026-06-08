## Context

When `opensddrag init` runs, it prompts users to select which AI tools to configure:
- Claude Code (writes `.mcp.json` + skills to `.claude/skills/` + commands to `.claude/commands/`)
- OpenCode (currently only writes `opencode.json` MCP config)

**Current bug**: OpenCode selection does NOT install any skills. The code at `client/src/commands/init.js:154-166` only loops through skill roots `.claude/skills` and `.agents/skills`, with no support for OpenCode's native skill format.

OpenCode skills require:
- Location: `.opencode/skills/<name>/SKILL.md`
- Frontmatter with `name`, `description`, and `compatibility: opencode`

## Goals / Non-Goals

**Goals:**
1. Install all 13 SDD skills to `.opencode/skills/` when OpenCode is selected
2. Add required frontmatter (`compatibility: opencode`) to each skill file
3. Maintain backward compatibility with Claude Code installation
4. No new external dependencies

**Non-Goals:**
1. Modify skill content/templates — existing templates work for both platforms
2. Create OpenCode-specific commands (OpenCode uses different command format)
3. Modify the MCP server or database schema
4. Add new skills beyond the existing 13

## Decisions

### 1. Create `.opencode/skills/` directory structure
**Chosen**: Create `.opencode/skills/<skill-name>/SKILL.md` alongside existing paths
**Alternative**: Modify `getSkills()` to return OpenCode-specific content
**Rationale**: Skills already exist in `client/src/templates/skills/index.js`. Adding a separate install step for OpenCode is simpler than duplicating or modifying templates.

### 2. Use existing skill template content with OpenCode frontmatter
**Chosen**: Wrap existing skill content with YAML frontmatter including `compatibility: opencode`
**Alternative**: Create entirely new OpenCode-specific skill templates
**Rationale**: Skill content is platform-agnostic (describes SDD workflow). Only the frontmatter format differs between platforms.

### 3. Maintain dual installation
**Chosen**: Install skills to ALL supported locations: `.claude/skills/`, `.agents/skills/`, AND `.opencode/skills/`
**Alternative**: Only install to OpenCode path when OpenCode is selected
**Rationale**: Users may use both Claude Code and OpenCode. Having skills available in all locations ensures consistency.

## Implementation Approach

### Modified file: `client/src/commands/init.js`

```javascript
// Add after line 166 (existing skill installation):
if (configuringOpenCode) {
  const opencodeSkillsRoot = join(cwd, ".opencode", "skills");
  for (const skill of skills) {
    const skillDir = join(opencodeSkillsRoot, skill.name);
    mkdirSync(skillDir, { recursive: true });
    const opencodeSkillContent = addOpencodeFrontmatter(skill);
    writeFileSync(join(skillDir, "SKILL.md"), opencodeSkillContent);
    configured.push(`skill → .opencode/skills/${skill.name}/SKILL.md`);
  }
}
```

### New helper function: `addOpencodeFrontmatter(skill)`

```javascript
function addOpencodeFrontmatter(skill) {
  return `---
name: ${skill.name}
description: ${extractDescription(skill.content)}
compatibility: opencode
---
${skill.content}`;
}
```

Where `extractDescription()` parses the first paragraph after the skill title for a 1-1024 char description.

## Risks / Trade-offs

- **Risk**: OpenCode may cache skills and not pick up new installations immediately
  - **Mitigation**: Document in output that user may need to restart OpenCode
- **Risk**: Skill descriptions exceeding 1024 characters
  - **Mitigation**: Truncate or summarize in `extractDescription()` function
- **Trade-off**: Slightly more disk usage with skills in 3 locations
  - **Mitigation**: Skills are small (~1KB each), 13 skills = ~39KB total