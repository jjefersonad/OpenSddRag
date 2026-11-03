/**
 * websec flow slash commands — installed as /opsr:websec:<command>.
 *
 * Each command is a structured prompt that points at the corresponding skill
 * (the single source of truth for the workflow). The command folder is
 * normalized to `opsr/websec` by client/src/flows.js `flowCommandFolder`, so the
 * raw `folder: "opsr"` mirrors the SDD pack and stays byte-stable.
 */

export function getCommands(slug, serverUrl) {
  const header = (name) => `> **IMPORTANT — ${name}**
> This command requires the **\`opensddrag\`** MCP server (${serverUrl}), configured in \`.mcp.json\`.
> All websec artifact reads/writes go through the OpenSddRag MCP tools. DO NOT create local files. DO NOT write markdown to disk.
> **If no OpenSddRag MCP tools are in your active tool list**: STOP immediately. Do NOT investigate or try alternatives. Tell the user: "The opensddrag MCP server is not connected. Please start it (\`docker compose up -d\`) and reload the project."
> **project_slug for every call: \`${slug}\`**

---
`;

  const pointerTail = (skillName) => `
## Step 1 — Load the skill
Invoke the \`${skillName}\` skill (Claude Code auto-loads it from \`.claude/skills/${skillName}/SKILL.md\` via the slash command; OpenCode loads it from \`.opencode/skills/${skillName}/SKILL.md\` via the \`skill\` tool).
The skill contains the complete workflow — MCP calls, templates, examples, edge cases. Follow it verbatim and do not duplicate its steps here.
`;

  return [
    {
      folder: "opsr",
      name: "scope",
      content: `${header("/opsr:websec:scope")}## Purpose
Establish the target, the authorized scope and the attack-surface inventory. Creates the
\`engagement\` and \`surface\` artifacts and records the context mode (in-progress / brownfield /
greenfield). This is the entry point of the websec flow.

## Input
$ARGUMENTS = target description (URL, repository or path) or an engagement brief.
${pointerTail("opensddrag-websec-scope")}`,
    },
    {
      folder: "opsr",
      name: "assess",
      content: `${header("/opsr:websec:assess")}## Purpose
Record the vulnerabilities discovered in the target as \`finding\` artifacts, each with severity,
CWE/OWASP reference and evidence, anchored to the source of truth for the change's context mode.

## Input
$ARGUMENTS = an aspect of the surface to assess, or empty to assess the whole surface.
${pointerTail("opensddrag-websec-assess")}`,
    },
    {
      folder: "opsr",
      name: "validate",
      content: `${header("/opsr:websec:validate")}## Purpose
Confirm each finding with a reproducible proof-of-concept (\`poc\`) linked to the finding it proves.

## Input
$ARGUMENTS = a finding name to validate, or empty to validate every finding.
${pointerTail("opensddrag-websec-validate")}`,
    },
    {
      folder: "opsr",
      name: "remediate",
      content: `${header("/opsr:websec:remediate")}## Purpose
Record the fix that resolves a finding as a \`remediation\` artifact linked back to that finding.

## Input
$ARGUMENTS = a finding name to remediate, or empty to remediate every open finding.
${pointerTail("opensddrag-websec-remediate")}`,
    },
    {
      folder: "opsr",
      name: "report",
      content: `${header("/opsr:websec:report")}## Purpose
Aggregate every finding of the change into a single \`report\`, grouped by severity and linking
each finding.

## Input
$ARGUMENTS = the change name (report covers all findings), or a severity filter.
${pointerTail("opensddrag-websec-report")}`,
    },
  ];
}

export const getOpenCodeCommands = getCommands;
