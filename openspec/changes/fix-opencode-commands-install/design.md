## Context

The current `opensddrag init` command writes slash commands to `.claude/commands/opsr/<command>.md` in Claude Code format. OpenCode uses a **different command format**:

**Claude Code format** (current):
- Location: `.claude/commands/opsr/<name>.md`
- Content: Full prompt with `/opsr:<name>` prefix references
- Invoked as: `/opsr:propose`, `/opsr:spec`, etc.

**OpenCode format** (required):
- Location: `.opencode/commands/<name>.md`
- Content: YAML frontmatter + prompt template
- Invoked as: `/propose`, `/spec`, `/design`, etc. (no `opsr:` prefix)

## Goals / Non-Goals

**Goals:**
1. Create OpenCode-compatible command templates with YAML frontmatter
2. Install 13 commands to `.opencode/commands/` when OpenCode is selected
3. Convert Claude Code command format to OpenCode format:
   - Remove `folder` concept (filename = command name)
   - Add YAML frontmatter with `description`, `agent`, `model`
   - Strip `/opsr:` prefixes from content (OpenCode uses `/<name>` directly)
4. Maintain backward compatibility with Claude Code commands

**Non-Goals:**
1. Modify the actual prompt content beyond format conversion
2. Create new commands beyond the existing 13
3. Modify MCP server behavior

## Decisions

### 1. Create new `getOpenCodeCommands()` template function
**Chosen**: Create `client/src/templates/commands/opencode.js` with `getOpenCodeCommands(slug, serverUrl)`
**Alternative**: Modify existing `getCommands()` to return different formats
**Rationale**: Separation of concerns. Keep Claude Code and OpenCode templates independent for easier maintenance.

### 2. Command naming convention
**Chosen**: Map `opsr:propose` → `propose` (filename: `propose.md`)
**Alternative**: Keep `opsr-propose` prefix
**Rationale**: OpenCode commands are project-global, not namespaced. Users invoke as `/propose`, not `/opsr:propose`.

### 3. Frontmatter structure
**Chosen**:
```yaml
---
description: Brief description of the command
agent: plan  # or build, custom
model: anthropic/...  # optional, use default if omitted
---
<prompt content>
```
**Alternative**: Put all commands in `opencode.json`
**Rationale**: Separate markdown files are easier to maintain and edit. Supports `$ARGUMENTS` placeholders naturally.

### 4. Content conversion strategy
**Chosen**: Transform Claude Code prompts by:
- Removing `$ARGUMENTS = /opsr:<name>` references
- Removing references to `/opsr:<other>` in content
- Keeping the actual prompt logic intact
**Alternative**: Rewrite all prompts from scratch
**Rationale**: The logic is the same; only the command invocation syntax differs. Transformation is faster and less error-prone.

## Implementation Approach

### New file: `client/src/templates/commands/opencode.js`

```javascript
export function getOpenCodeCommands(slug, serverUrl) {
  return [
    {
      name: "propose",
      description: "Create a named change with proposal artifact",
      agent: "plan",
      // agent, model optional - omit if using defaults
      content: `...prompt content...`
    },
    // ... 12 more commands
  ];
}
```

### Modified file: `client/src/commands/init.js`

Add OpenCode command installation after skill installation:

```javascript
// Install OpenCode-native commands if OpenCode is selected
if (selectedTools.includes("OpenCode")) {
  const opencodeCommandsRoot = join(cwd, ".opencode", "commands");
  const opencodeCommands = getOpenCodeCommands(slug, serverUrl);
  for (const cmd of opencodeCommands) {
    const cmdPath = join(opencodeCommandsRoot, `${cmd.name}.md`);
    mkdirSync(opencodeCommandsRoot, { recursive: true });
    const content = `---
description: ${cmd.description}
${cmd.agent ? `agent: ${cmd.agent}` : ''}
${cmd.model ? `model: ${cmd.model}` : ''}
---

${cmd.content}`;
    writeFileSync(cmdPath, content);
    configured.push(`command → .opencode/commands/${cmd.name}.md`);
  }
}
```

### Content transformation function

```javascript
function convertToOpenCodeFormat(claudeCodeContent, commandName) {
  return claudeCodeContent
    .replace(/\$ARGUMENTS = \/opsr:<command>/g, `$ARGUMENTS = /${commandName}`)
    .replace(/\/opsr:<command>/g, `/${commandName}`)
    .replace(/(\\|\/)opsr:([a-z]+)/g, '/$2')  // remove opsr: prefix globally
    .trim();
}
```

## Risks / Trade-offs

- **Risk**: Frontmatter parsing errors if description contains colons
  - **Mitigation**: Use YAML multi-line strings or escape colons
- **Risk**: OpenCode cache may not pick up new commands immediately
  - **Mitigation**: Document that restart may be needed
- **Trade-off**: Slightly more disk usage with dual command installation
  - **Mitigation**: Commands are small (~1KB each), 13 commands = ~26KB total