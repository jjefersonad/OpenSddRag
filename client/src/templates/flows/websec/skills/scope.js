export const scopeSkill = {
  name: "opensddrag-websec-scope",
  description:
    "websec: establish target, authorization and attack-surface inventory before assessment",
  body: (slug, note) => `# OpenSddRag — websec: Scope
${note}## When to use
Entry point for the \`websec\` flow. Establish the target, the authorized scope and the
attack-surface inventory BEFORE any assessment. Produces the \`engagement\` and \`surface\`
artifacts and records the context mode. Never assess without an authorized \`engagement\`.

## Inputs
$ARGUMENTS = target description (URL, repository or path) or an engagement brief.

## Workflow

### Step 1 — Detect the context mode
Determine which of three situations the target is in and keep it as \`context_mode\`:
- **in-progress** — the project already exists in the DB AND planning artifacts exist.
  Signals: the slug is registered, and
  \`search_semantic(query="$ARGUMENTS", project_slug="${slug}")\` returns proposals/specs/designs.
- **brownfield** — the working directory contains application code but the project has
  no planning artifacts.
- **greenfield** — no code and no planning artifacts; only intent/design documents exist.

Client-side, read-only inspection of the working directory decides "is there code?" —
the MCP server cannot see the target filesystem. Do NOT write any files.

### Step 2 — Create the engagement (authorization gate)
The \`engagement\` artifact is the precondition for every finding. Create it with the
required metadata keys \`target\`, \`authorization\` and \`scope\`:
\`create_artifact(name="<change>-engagement", type="engagement", content="<scope · authorization · rules of engagement · out of scope>", metadata={"change_name": "<change>", "target": "<target>", "authorization": "<authorized-by / reference>", "scope": "<in-scope assets>", "context_mode": "<mode>"}, project_slug="${slug}")\`
The content MUST include the headings \`## Scope\`, \`## Authorization\`,
\`## Rules of Engagement\` and \`## Out of Scope\`. Then
\`validate_artifact(name="<change>-engagement", project_slug="${slug}")\`.
If the user has not confirmed authorization, STOP and ask — never proceed without it.

### Step 3 — Create the surface bootstrap artifact
Create exactly one \`surface\` artifact, derived from the source of truth for the mode:
- **in-progress** → derive from the existing specs/designs plus the code;
- **brownfield** → enumerate routes/entry points discovered in the code;
- **greenfield** → enumerate the proposed architecture's trust boundaries.
\`create_artifact(name="<change>-surface", type="surface", content="<entry points · trust boundaries>", metadata={"change_name": "<change>", "context_mode": "<mode>", "source": "<specs|code|design-intent>"}, project_slug="${slug}")\`

### Step 4 — Record the action
\`record_trace(action="websec_scope", result_summary="scope: context_mode=<mode>, engagement+surface created", project_slug="${slug}")\`

## Output
- A validated \`engagement\` artifact and a \`surface\` bootstrap artifact.
- **Unlocks:** /opsr:websec:assess.

## Important rules
- No \`finding\` or \`poc\` may be created before a valid \`engagement\` exists.
- The gate is a process control, not a security boundary — enforce it honestly.
- All artifacts live in the database; do NOT create local markdown files.
`,
};
