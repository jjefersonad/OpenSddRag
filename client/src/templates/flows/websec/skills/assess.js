export const assessSkill = {
  name: "opensddrag-websec-assess",
  description:
    "websec: record vulnerability findings with severity, CWE/OWASP reference and evidence",
  body: (slug, note) => `# OpenSddRag — websec: Assess
${note}## When to use
After \`/opsr:websec:scope\` has produced a validated \`engagement\` and a \`surface\`
artifact. Record the vulnerabilities discovered in the target as \`finding\` artifacts,
each anchored to the source of truth for the change's \`context_mode\`.

## Inputs
$ARGUMENTS = an aspect of the surface to assess, or empty to assess the whole surface.

## Workflow

### Step 1 — Confirm the gate and the mode
\`read_artifact(name="<change>-engagement", project_slug="${slug}")\` MUST exist and be
valid; otherwise STOP and run /opsr:websec:scope first. Then read the \`surface\`
artifact and take \`context_mode\` from its metadata.

### Step 2 — Inspect the target
Read only. Inspect the code / running app against the \`surface\` entry points. Do NOT
modify the target and do NOT run destructive payloads — this flow records findings, it
does not exploit beyond a read-only reproduction.

### Step 3 — Create one \`finding\` per vulnerability
Each finding MUST carry the required metadata keys \`severity\`, \`reference\`
(CWE/OWASP) and \`evidence\`, and the required headings \`## Affected Component\`,
\`## Reproduction\`, \`## Impact\`, \`## Remediation\`:
\`create_artifact(name="<change>-finding-<N>", type="finding", content="<affected component · reproduction · impact · remediation>", metadata={"change_name": "<change>", "severity": "<critical|high|medium|low>", "reference": "<CWE-xxx / OWASP A0x>", "evidence": "<observation>", "context_mode": "<mode>"}, project_slug="${slug}")\`
Then \`validate_artifact(name="<change>-finding-<N>", project_slug="${slug}")\`.

### Step 4 — Anchor the finding to the mode
- **in-progress** → link to the relevant planning artifact:
  \`link_artifacts(source_name="<change>-finding-<N>", target_name="<spec-or-design>", relationship_type="relates_to", project_slug="${slug}")\`
- **brownfield** → record \`file\`, \`line\` and \`git_sha\` on the finding metadata
  (collected client-side, since the server cannot read the repository);
- **greenfield** → link to the design/intent artifact, or leave unanchored with a note.

### Step 5 — Record the action
\`record_trace(action="websec_assess", result_summary="assess: <N> findings recorded", project_slug="${slug}")\`

## Output
- One validated \`finding\` artifact per vulnerability, anchored per the change's mode.
- **Unlocks:** /opsr:websec:validate.

## Important rules
- No \`finding\` without an existing validated \`engagement\`.
- Never fabricate a finding: \`evidence\` MUST reflect an actual observation.
- All artifacts live in the database; do NOT create local markdown files.
`,
};
