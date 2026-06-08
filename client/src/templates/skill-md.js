export function renderSkillMd({ slug, serverUrl }) {
  return `# OpenSddRag — SDD + Harness

This project is connected to the OpenSddRag Harness (${serverUrl}).
Use the MCP tools below to follow Spec-Driven Development with persistent semantic memory.

## Project slug: \`${slug}\`

Always pass \`project_slug: "${slug}"\` to scope queries to this project.
Use \`project_slug: "*"\` to search across all projects.

## When to start

Before implementing any feature, always check for existing specs:

\`\`\`
search_semantic(query="<topic>", project_slug="${slug}")
\`\`\`

Then pick the right SDD skill:

\`\`\`
suggest_skill(objective="<your goal>", project_slug="${slug}")
\`\`\`

## SDD Skills (built-in)

| Skill | When to use |
|-------|-------------|
| \`sdd:propose\` | Before anything — write intent and scope |
| \`sdd:spec\` | After proposal — Purpose / Requirements / Scenarios |
| \`sdd:design\` | After spec — technical decisions and trade-offs |
| \`sdd:tasks\` | After design — decompose into atomic tasks (<4h each) |
| \`sdd:apply\` | Execute tasks against spec acceptance criteria |
| \`sdd:full-flow\` | Run all steps above in sequence |

## Memory tools

| Tool | Purpose |
|------|---------|
| \`search_semantic\` | Find specs/tasks by topic (semantic) |
| \`recall_episodes\` | Find past agent actions (episodic memory) |
| \`get_working_context\` | See the active session and focused artifacts |
| \`update_working_context\` | Set which artifacts you are working on |
| \`record_trace\` | Log what you just did (builds episodic memory) |

## SDD Artifact tools

| Tool | Purpose |
|------|---------|
| \`create_artifact\` | Create proposal / spec / change / task / design |
| \`read_artifact\` | Read a specific artifact by name |
| \`list_artifacts\` | List artifacts with type/status filters |
| \`update_artifact\` | Update content or status |
| \`validate_artifact\` | Check spec structure |
| \`link_artifacts\` | Link artifacts (implements / depends_on / relates_to) |
| \`get_relationships\` | Get related artifacts |

## Full flow example

\`\`\`
1. suggest_skill(objective="add JWT authentication", project_slug="${slug}")
   → returns "sdd:full-flow"

2. get_skill(name="sdd:propose", project_slug="${slug}")
   → follow the steps to create a proposal

3. create_artifact(name="auth-jwt-proposal", type="proposal",
     content="...", project_slug="${slug}")

4. ... follow sdd:spec, sdd:design, sdd:tasks, sdd:apply
\`\`\`
`;
}
