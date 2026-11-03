export const reportSkill = {
  name: "opensddrag-websec-report",
  description:
    "websec: aggregate findings into a report grouped by severity",
  body: (slug, note) => `# OpenSddRag — websec: Report
${note}## When to use
At the close of a \`websec\` engagement. Aggregate every \`finding\` of the change into a
single \`report\`, grouped by severity and linking each finding.

## Inputs
$ARGUMENTS = the change name (report covers all findings), or a severity filter.

## Workflow

### Step 1 — Collect the findings
\`list_artifacts(type="finding", flow="websec", project_slug="${slug}")\` and filter by
\`metadata.change_name\`. Read each finding's \`severity\`.

### Step 2 — Create the report
Group findings by the same \`severity\` vocabulary used on the findings
(\`critical|high|medium|low\`). The report MUST include the headings
\`## Summary\` and \`## Findings by Severity\`, and reference every finding:
\`create_artifact(name="<change>-report", type="report", content="<summary · findings grouped by severity>", metadata={"change_name": "<change>", "finding_count": "<N>"}, flow="websec", project_slug="${slug}")\`
Then \`validate_artifact(name="<change>-report", project_slug="${slug}")\`.

### Step 3 — Link the report to each finding
For each finding: \`link_artifacts(source_name="<change>-report", target_name="<change>-finding-<N>", relationship_type="relates_to", project_slug="${slug}")\`

### Step 4 — Record the action
\`record_trace(action="websec_report", result_summary="report: <N> findings aggregated", project_slug="${slug}")\`

## Output
- One \`report\` artifact grouped by severity, linking every finding.

## Important rules
- Group by the SAME severity key carried on the findings (no drift).
- Every finding MUST be referenced by the report.
- All artifacts live in the database; do NOT create local markdown files.
`,
};
