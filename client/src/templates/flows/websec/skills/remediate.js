export const remediateSkill = {
  name: "opensddrag-websec-remediate",
  description:
    "websec: record the remediation that resolves a finding",
  body: (slug, note) => `# OpenSddRag — websec: Remediate
${note}## When to use
After a \`finding\` (and ideally its \`poc\`) exists. Record the fix that resolves the
finding as a \`remediation\` artifact linked back to that finding.

## Inputs
$ARGUMENTS = a finding name to remediate, or empty to remediate every open finding.

## Workflow

### Step 1 — Pick the finding
\`read_artifact(name="<change>-finding-<N>", project_slug="${slug}")\` and read its
\`## Remediation\` heading.

### Step 2 — Create the remediation
\`create_artifact(name="<change>-remediation-<N>", type="remediation", content="<what was changed · why it resolves the finding · retest result>", metadata={"change_name": "<change>", "finding": "<change>-finding-<N>"}, project_slug="${slug}")\`

### Step 3 — Link the remediation to its finding
\`link_artifacts(source_name="<change>-remediation-<N>", target_name="<change>-finding-<N>", relationship_type="relates_to", project_slug="${slug}")\`

### Step 4 — Record the action
\`record_trace(action="websec_remediate", result_summary="remediate: remediation created for <finding>", project_slug="${slug}")\`

## Output
- One \`remediation\` artifact per resolved finding, linked via \`relates_to\`.
- **Unlocks:** /opsr:websec:report.

## Important rules
- Every \`remediation\` MUST link to the \`finding\` it resolves via \`relates_to\`.
- Note the retest outcome; a remediation without a retest is unverified.
- All artifacts live in the database; do NOT create local markdown files.
`,
};
