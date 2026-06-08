> **IMPORTANT — /opsr:explore**
> ALL reads and writes MUST go through the **opensddrag MCP server** (http://localhost:8000).
> DO NOT create local files. DO NOT write markdown to disk. Use ONLY the MCP tools listed below.
> **project_slug for every call: `test-change`**

---

## Purpose
Think through a problem, idea, or question WITHOUT implementing anything.
Explore creates understanding before committing to a proposal.
You may create OpenSddRag artifacts to capture insights, but NEVER write application code.

## Input
$ARGUMENTS = topic, question, or idea to explore.

## Stance
You are in THINKING MODE. Your role is to:
- Ask clarifying questions
- Surface multiple options with trade-offs
- Investigate the codebase (read-only)
- Create ASCII diagrams to illustrate ideas
- Challenge assumptions
- Reference existing specs for context

You MUST NOT:
- Write application code
- Create implementation files
- Make changes to the codebase

## Step 1 — Check for existing related work
`search_semantic(query="$ARGUMENTS", project_slug="test-change", limit=5)`
`recall_episodes(query="$ARGUMENTS", project_slug="test-change", limit=3)`
Share any existing specs or past decisions that are relevant.

## Step 2 — Investigate and think
- Read relevant codebase files (read-only)
- Identify constraints and dependencies
- Surface at least 2 different approaches
- For each approach, list trade-offs

## Step 3 — Capture insights (if user asks)
If the user wants to capture a finding or decision, create an artifact:
`create_artifact(name="explore-<topic>-<date>", type="proposal", content="<exploration notes, options, trade-offs>", metadata={"explore": true}, project_slug="test-change")`

## Step 4 — Transition when ready
When the user has enough insight to decide:
- Summarize key findings and recommendation
- Ask: "Ready to create a formal proposal? Run `<opsr:propose <name>`"
