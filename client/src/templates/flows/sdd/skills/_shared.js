/**
 * Shared helpers for OpenSddRag skill templates.
 *
 * Each skill lives in its own module (propose.js, spec.js, …) and exports an
 * object: { name, description, body(slug, note) }. The aggregator in index.js
 * wraps `body` with the Claude Code or OpenCode header (`note`) and the YAML
 * frontmatter, so the workflow is authored exactly once and the CC/OC pair is
 * always in sync (command-skill-separation-contract REQ-001).
 */

/**
 * Renders the reusable harness phase-gate checklist block, inlined into the
 * spec/apply/verify/archive skills at the point just before the phase gate.
 * Mirrors the legacy harnessChecklistStep() that used to live in the command
 * templates.
 */
export function harnessChecklistBlock(slug, trigger, gateLabel) {
  return `### Step — Harness checklist (${trigger})
Call the MCP tool to load all enabled harness rules for the \`${trigger}\` trigger:
\`get_harness_checklist(trigger="${trigger}", project_slug="${slug}")\`

Process the response:
- **If the result is an empty array \`[]\`** → output "No harness rules for this trigger." and continue.
- **If any rule has \`severity="error"\`** → present it as:
  \`\`\`
  MUST complete before proceeding (${gateLabel}):
  - [<name>] <instruction>
  \`\`\`
  Then \`STOP\` and wait until each error-severity rule is confirmed satisfied before continuing.
- **If any rule has \`severity="warning"\`** → present it as "SHOULD complete: [<name>] <instruction>" (advisory; proceed if satisfied).
- **If any rule has \`severity="info"\`** → present inline as "Info: [<name>] <instruction>" and proceed.
- Rules are returned sorted error-first then by name; preserve that order when displaying.
- This step MUST run BEFORE ${gateLabel.toLowerCase()}.
`;
}
