export function getHarnessSkill({ slug, serverUrl }) {
  // SKILL.md for the `opensddrag-harness` skill — installed into
  // .claude/skills/opensddrag-harness/ and .agents/skills/opensddrag-harness/
  // by `opensddrag init`. Drives the /opsr:harness slash command behaviorally
  // for both Claude Code and OpenCode, using only the standard MCP tools
  // (add_rule, list_rules, get_harness_checklist). No direct DB access, no
  // local file writes for rule storage — rules are persisted via the MCP
  // server's `project_rules` table.
  return `---
name: opensddrag-harness
description: Manage persistent project rules — add, list, and disable behavioral constraints
---

# OpenSddRag — Harness

This project is connected to the OpenSddRag Harness (${serverUrl}).
The Harness layer manages **project rules**: persistent, per-project behavioral
constraints that are automatically injected into every agent session.

## Project slug: \`${slug}\`

Always pass \`project_slug: "${slug}"\` to scope rule operations to this project.

## When to use

- Before starting any new feature, ask: "Are there harness rules I should be aware of?"
  \`get_working_context(project_slug="${slug}")\` will return any \`trigger="always"\` rules
  automatically — read them first.
- Use \`/opsr:harness\` (Claude Code) or invoke this skill (OpenCode) to:
  - **add** a new rule (architecture, naming, forbidden, doc-sync, verification)
  - **list** all rules for the project, grouped by trigger
  - **disable** a rule (soft-delete — re-enable by re-adding with the same name)

## Available operations

### add — create or update a project rule

Call the \`add_rule\` MCP tool. Required arguments:

\`\`\`
add_rule(
  name:        "<kebab-case-name>",
  trigger:     "always" | "on_apply" | "on_verify" | "on_archive" | "on_spec",
  category:    "architecture" | "naming" | "forbidden" | "doc-sync" | "verification",
  severity:    "error" | "warning" | "info",   // default: "warning"
  instruction: "<free-text rule the agent must follow>",
  project_slug:"${slug}",
  enabled:     true,                              // default: true (set false to soft-delete)
  metadata:    { ... }                            // optional, free-form JSON
)
\`\`\`

When the user provides a rule in natural language, infer the fields:
- "always update X when applying" → trigger=\`on_apply\`, category=\`doc-sync\`, severity=\`warning\`
- "never do Y" → trigger=\`always\`, category=\`forbidden\`, severity=\`error\`
- "use Z pattern in this project" → trigger=\`always\`, category=\`architecture\`, severity=\`warning\`

**Example 1 — architecture rule (always):**
\`\`\`
add_rule(
  name:        "repo-pattern-required",
  trigger:     "always",
  category:    "architecture",
  severity:    "error",
  instruction: "All data access must go through a repository class. Do not call the ORM or DB driver directly from route handlers or service classes.",
  project_slug:"${slug}"
)
\`\`\`

**Example 2 — doc-sync rule (on_apply):**
\`\`\`
add_rule(
  name:        "update-changelog-on-apply",
  trigger:     "on_apply",
  category:    "doc-sync",
  severity:    "warning",
  instruction: "When applying a task that ships a user-visible change, add a one-line entry to CHANGELOG.md under the unreleased section before marking the task complete.",
  project_slug:"${slug}"
)
\`\`\`

Confirm with the user after adding:
"Rule '<name>' added. It will be [injected at every session start | checked during /opsr:apply | ...]."

### list — show all rules for this project

Call the \`list_rules\` MCP tool:

\`\`\`
list_rules(project_slug="${slug}", enabled_only=true)
\`\`\`

Group the results by \`trigger\` in the output:

\`\`\`
### Always (loaded at session start)
- [architecture:error] repo-pattern-required — All data access must go through...

### On Apply (checked during /opsr:apply)
- [doc-sync:warning] update-changelog-on-apply — When applying a task...

### On Verify (checked during /opsr:verify)
- (none)

### On Archive (checked during /opsr:archive)
- (none)

### On Spec (checked during /opsr:spec)
- (none)
\`\`\`

If the result list is empty, respond:
"No harness rules defined for this project. Run \`/opsr:harness add\` to create the first rule."

### disable — soft-delete a rule

Call the \`add_rule\` MCP tool with the same \`name\` and \`enabled=false\`:

\`\`\`
add_rule(name: "<rule-name>", enabled: false, project_slug: "${slug}")
\`\`\`

This is a soft-delete: the rule is preserved in the database with \`enabled=false\`
and will no longer appear in \`list_rules\` (default \`enabled_only=true\`) or in
\`get_working_context\` injection. To re-enable, call \`add_rule\` with the same
name and \`enabled=true\`.

Confirm with the user:
"Rule '<name>' disabled. It will no longer appear in checklists or session context."

## Phase-gate checklist — get_harness_checklist

When the user runs \`/opsr:apply\`, \`/opsr:verify\`, \`/opsr:archive\`, or
\`/opsr:spec\`, the corresponding slash command will call:

\`\`\`
get_harness_checklist(trigger="on_apply"|"on_verify"|"on_archive"|"on_spec", project_slug="${slug}")
\`\`\`

…to fetch rules that must be satisfied at that phase gate. The response is an
array of {name, category, severity, instruction} objects ordered by severity
(error first) then name. Rules with \`severity="error"\` MUST be completed before
the phase is declared done; \`severity="warning"\` rules SHOULD be addressed.

You do not need to call this directly — the slash commands invoke it. But you
can use it from this skill if the user asks "what rules apply to apply?".

## Memory of rule operations

Every add / disable operation should be recorded in episodic memory:

\`\`\`
record_trace(action="add_rule"|"disable_rule", result_summary="Added/disabled rule: <name>", project_slug="${slug}")
\`\`\`

## MCP tools used

| Tool | Purpose |
|------|---------|
| \`add_rule\` | Upsert a rule (create, update, or soft-delete) |
| \`list_rules\` | List rules with optional filters |
| \`get_harness_checklist\` | Fetch phase-gate rules for apply/verify/archive/spec |
| \`get_working_context\` | Already returns trigger="always" rules automatically |
| \`record_trace\` | Log harness operations to episodic memory |

## Important rules for this skill

- **Never write rule data to local files** — all rules live in the \`project_rules\` table.
- **Never translate or modify the user's rule instruction** — store it verbatim.
- **Always confirm with the user before calling \`add_rule\`** for new rules, especially when inferring fields from natural language.
- **Soft-delete is the only way to "remove" a rule** — re-adding with the same name restores it.
`;
}

export function getOpenCodeHarnessSkill({ slug, serverUrl }) {
  const full = getHarnessSkill({ slug, serverUrl });
  // OpenCode auto-discovers tools from opencode.json — the table is noise.
  return full.replace(/\n## MCP tools used\n[\s\S]*?(?=\n## |\n$)/, '\n');
}

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
