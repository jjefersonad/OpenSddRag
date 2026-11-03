export const exploreSkill = {
  name: "opensddrag-explore",
  description: "Investigate a problem or idea without writing any code",
  body: (slug, note) => `# OpenSddRag — Explore
${note}## When to use
Thinking mode — to investigate a problem, idea, or question and build understanding BEFORE
committing to a proposal. You may capture insights as artifacts, but you NEVER write code here.

## Inputs
$ARGUMENTS = topic, question, or idea to explore.

## Stance
You are in THINKING MODE. Your role is to:
- Ask clarifying questions.
- Surface at least two options with trade-offs.
- Investigate the codebase (read-only).
- Create ASCII diagrams to illustrate ideas.
- Challenge assumptions and reference existing specs for context.

You MUST NOT:
- Write application code.
- Create implementation files.
- Make changes to the codebase.

## Workflow

### Step 1 — Check for existing related work
\`search_semantic(query="$ARGUMENTS", project_slug="${slug}", limit=5)\`
\`recall_episodes(query="$ARGUMENTS", project_slug="${slug}", limit=3)\`
Share any existing specs or past decisions that are relevant.

### Step 2 — Investigate and think
- Read relevant codebase files (read-only).
- Identify constraints and dependencies.
- Surface at least two different approaches; for each, list trade-offs.

### Step 3 — Capture insights (only if the user asks)
\`create_artifact(name="explore-<topic>-<date>", type="proposal", content="<exploration notes, options, trade-offs>", metadata={"explore": true}, project_slug="${slug}")\`
If amending an existing design/proposal, use \`update_artifact\` instead.

### Step 4 — Transition when ready
Summarize the key findings and a recommendation, then ask:
"Ready to create a formal proposal? Run /opsr:propose <name>."

## Example prompts this skill handles well
- "Is it coherent to refactor X this way?" → validate the premise against the code, surface risks.
- "Two ways to model Y — which is better here?" → compare approaches with trade-offs and a pick.
- "What would it take to add Z?" → scope the work, list constraints and dependencies, no code.

## Output shape
A short written analysis: premise check → 2+ options with trade-offs → a recommendation →
optional follow-up actions (amend a design, create an explore-* artifact, or move to /opsr:propose).

## Output
- Shared analysis and a recommendation; optionally an \`explore-*\` artifact capturing the decision.

## Important rules
- NEVER write application code or create implementation files in this phase.
- Only create/update OpenSddRag artifacts when the user explicitly asks to capture something.
- Prefer presenting trade-offs and a recommendation over an exhaustive survey.
`,
};
