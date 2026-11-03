/**
 * websec flow manifest — the authoring source for the `websec` flow.
 *
 * Shape follows client-cli REQ-011 / flow-registry REQ-001: a flow is a named
 * pack of `kinds` (with optional declarative validation rules), `lifecycle`
 * phases, `harnessTriggers`, `rules`, `skills`, `commands` and a
 * `claudeMdSection` that `init` installs. `init` reads this to decide which
 * skill/command files to write and (for non-`sdd` flows) registers the
 * manifest with the server.
 *
 * `rules` is a client-only extension (websec-flow design D5): the seed loop in
 * `init` reads it and upserts each rule via the `add_rule` tool, so the
 * authorization gate ships with the flow without a server schema change.
 */

export const websecManifest = {
  flow: "websec",
  kinds: [
    {
      kind: "engagement",
      required_headings: ["Scope", "Authorization", "Rules of Engagement", "Out of Scope"],
      required_metadata_keys: ["target", "authorization", "scope"],
    },
    {
      kind: "surface",
      required_headings: ["Entry Points", "Trust Boundaries"],
      required_metadata_keys: ["context_mode"],
    },
    {
      kind: "finding",
      required_headings: ["Affected Component", "Reproduction", "Impact", "Remediation"],
      required_metadata_keys: ["severity", "reference", "evidence"],
    },
    { kind: "poc" },
    { kind: "remediation" },
    {
      kind: "report",
      required_headings: ["Summary", "Findings by Severity"],
    },
  ],
  harnessTriggers: ["always", "on_apply", "on_verify"],
  lifecycle: [
    { name: "Scope", kinds: ["engagement"] },
    { name: "Recon", kinds: ["surface"] },
    { name: "Model", kinds: ["surface"] },
    { name: "Assess", kinds: ["finding"] },
    { name: "Validate", kinds: ["poc"] },
    { name: "Remediate", kinds: ["remediation"] },
    { name: "Report", kinds: ["report"] },
  ],
  rules: [
    {
      name: "websec-authorization-gate",
      trigger: "on_apply",
      category: "verification",
      severity: "error",
      instruction:
        "Before creating any `finding` or `poc` for a `websec` change, an `engagement` artifact declaring `target`, `authorization` and `scope` MUST exist. If none exists, STOP and create the `engagement` first.",
    },
  ],
  skills: [
    "opensddrag-websec-scope",
    "opensddrag-websec-assess",
    "opensddrag-websec-validate",
    "opensddrag-websec-remediate",
    "opensddrag-websec-report",
  ],
  commands: [
    { name: "scope", folder: "opsr" },
    { name: "assess", folder: "opsr" },
    { name: "validate", folder: "opsr" },
    { name: "remediate", folder: "opsr" },
    { name: "report", folder: "opsr" },
  ],
  claudeMdSection: `## OpenSddRag — Web Security Analysis (websec)

This project uses the **websec** OpenSddRag flow for authorized web-vulnerability analysis.

- **Commands:** \`.claude/commands/opsr/websec/\` (invoked as \`/opsr:websec:<command>\`)

### websec Flow

\`\`\`
/opsr:websec:scope → /opsr:websec:assess → /opsr:websec:validate → /opsr:websec:remediate → /opsr:websec:report
\`\`\`

An \`engagement\` artifact declaring target, authorization and scope MUST exist before any finding.
`,
};

export default websecManifest;
