export function renderClaudeMdBlock({ slug, serverUrl }) {
  return `
---

## OpenSddRag — SDD + Harness

This project uses **OpenSddRag** for Spec-Driven Development with persistent semantic memory.

- **MCP server name:** \`opensddrag\` (${serverUrl}) — configured in \`.mcp.json\`
- **Project slug:** \`${slug}\`
- **Skills:** \`.claude/skills/opensddrag-*/SKILL.md\`
- **Commands:** \`.claude/commands/opsr/\`

### MCP Tools (opensddrag server)

The \`opensddrag\` MCP server exposes these tools — they appear in your tool list under the \`opensddrag\` namespace:

| Tool | Purpose |
|------|---------|
| \`create_artifact\` | Create proposals, specs, designs, tasks |
| \`read_artifact\` | Read an artifact by name |
| \`list_artifacts\` | List artifacts with type/status filters |
| \`update_artifact\` | Update content or status |
| \`validate_artifact\` | Check spec structure |
| \`link_artifacts\` | Link artifacts (implements / depends_on / relates_to) |
| \`get_relationships\` | Get linked artifacts |
| \`search_semantic\` | Semantic search via pgvector |
| \`recall_episodes\` | Find past agent actions (episodic memory) |
| \`get_working_context\` | Get active session context |
| \`update_working_context\` | Update session context |
| \`record_trace\` | Log an action to episodic memory |

> If these tools are NOT in your active tool list, the server is not connected.
> Start it with \`docker compose up -d\` and reload the project. Do not attempt to work around a missing server.

### Before implementing any feature

Always search for existing specs first:

\`\`\`
search_semantic(query="<topic>", project_slug="${slug}")
\`\`\`

### SDD Commands

| Command | When to use |
|---------|-------------|
| \`/opsr:propose\` | Start here — capture intent and scope before any code |
| \`/opsr:spec\` | Formalize requirements (Purpose / SHALL / Scenarios) |
| \`/opsr:design\` | Document technical decisions and trade-offs |
| \`/opsr:tasks\` | Decompose spec into atomic tasks (< 4h each) |
| \`/opsr:apply\` | Implement the next pending task against spec criteria |
| \`/opsr:flow\` | Run the full flow end-to-end for a feature |
| \`/opsr:search\` | Semantic search over specs and past work |
| \`/opsr:status\` | Show what's in progress and what's done |
| \`/opsr:archive\` | Mark a completed feature as archived |

### SDD Flow

\`\`\`
/opsr:propose → /opsr:spec → /opsr:design → /opsr:tasks → /opsr:apply → /opsr:archive
\`\`\`
`;
}

export function renderClaudeMdStandalone({ projectName, slug, serverUrl }) {
  return `# ${projectName}
${renderClaudeMdBlock({ slug, serverUrl })}`;
}
