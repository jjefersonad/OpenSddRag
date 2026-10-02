export const searchSkill = {
  name: "opensddrag-search",
  description: "Semantic search over specs, tasks, and past agent actions",
  body: (slug, note) => `# OpenSddRag — Search
${note}## When to use
To search the SDD knowledge base by semantic similarity (pgvector). Run this BEFORE starting any
new work to find existing specs, decisions, and past implementations.

## Inputs
$ARGUMENTS = natural language search query.

## Workflow

### Step 1 — Search this project
\`search_semantic(query="$ARGUMENTS", project_slug="${slug}", limit=5)\`

### Step 2 — If no relevant results, search all projects
\`search_semantic(query="$ARGUMENTS", project_slug="*", limit=5)\`

### Step 3 — Recall past actions related to the query
\`recall_episodes(query="$ARGUMENTS", project_slug="${slug}", limit=3)\`

### Step 4 — Present the results clearly
For each result: name, type, status, and a content excerpt (first ~200 chars).
Group by: this project / other projects / past actions.

### Step 5 — Offer to read a full artifact
\`read_artifact(name="<artifact-name>", project_slug="${slug}")\`

### Step 6 — Optionally filter by artifact type
When the user is only interested in one kind of artifact, narrow the search:
\`search_semantic(query="$ARGUMENTS", project_slug="${slug}", type="spec", limit=5)\`
Valid \`type\` values: \`proposal\`, \`spec\`, \`design\`, \`task\`.

## Examples
- "How do we handle delta specs?" → finds the spec/sync capability artifacts.
- "auth token refresh" → finds proposals/specs/designs touching authentication.
- "what did we decide about embeddings" → combine with \`recall_episodes\` for past decisions.

A good presentation block looks like:
\`\`\`
### This project
- [spec] opensddrag-sync-spec (active) — "Merges delta specs (ADDED/MODIFIED/REMOVED…)"
### Other projects
- (none)
### Past actions
- design (2026-06-22) — "Created design: refactor-commands-skills-separation-design"
\`\`\`

## Output
- A grouped list of semantically relevant artifacts and past actions, with an offer to open any.

## Important rules
- Read-only — search never creates or modifies artifacts.
- Fall back to cross-project search (project_slug="*") only when the local search is empty.
- Surface episodic recall alongside artifacts so prior decisions are not missed.
- Prefer specific, noun-rich queries; vague one-word queries return weak matches.
- Always run search BEFORE /opsr:propose to avoid creating duplicate changes.
`,
};
