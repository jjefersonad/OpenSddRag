export const validateSkill = {
  name: "opensddrag-websec-validate",
  description:
    "websec: record a proof-of-concept that reproduces a finding",
  body: (slug, note) => `# OpenSddRag — websec: Validate
${note}## When to use
After \`/opsr:websec:assess\` has recorded one or more \`finding\` artifacts. Confirm each
finding with a reproducible proof-of-concept (\`poc\`), linked to the finding it proves.

## Inputs
$ARGUMENTS = a finding name to validate, or empty to validate every finding.

## Workflow

### Step 1 — Pick the finding
\`read_artifact(name="<change>-finding-<N>", project_slug="${slug}")\`. Validate its
\`evidence\` against the actual target (read-only). Never mutate the target.

### Step 2 — Create the poc
\`create_artifact(name="<change>-poc-<N>", type="poc", content="<reproduction steps · expected vs observed>", metadata={"change_name": "<change>", "finding": "<change>-finding-<N>"}, project_slug="${slug}")\`

### Step 3 — Link the poc to its finding
\`link_artifacts(source_name="<change>-poc-<N>", target_name="<change>-finding-<N>", relationship_type="implements", project_slug="${slug}")\`

### Step 4 — Record the action
\`record_trace(action="websec_validate", result_summary="validate: poc created for <finding>", project_slug="${slug}")\`

## Output
- One \`poc\` artifact per validated finding, linked via \`implements\`.
- **Unlocks:** /opsr:websec:remediate.

## Important rules
- Every \`poc\` MUST link to exactly one \`finding\` via \`implements\`.
- The reproduction is read-only; do not run destructive payloads.
- All artifacts live in the database; do NOT create local markdown files.
`,
};
