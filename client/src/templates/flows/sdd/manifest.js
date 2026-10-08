/**
 * SDD flow manifest — the authoring source for the built-in `sdd` flow.
 *
 * Shape follows client-cli REQ-011 / flow-registry REQ-001: a flow is a
 * named pack of `kinds`, `harnessTriggers`, `skills`, `commands` and a
 * `claudeMdSection` that `init` installs. `init` reads this to decide
 * which skill/command files to write and (for non-`sdd` flows) registers
 * the manifest with the server.
 *
 * SDD keeps bare `/opsr:<command>` command paths (no `sdd/` subfolder),
 * so every command is declared with `folder: "opsr"` and identity
 * identifiers (`opensddrag-<command>`) unchanged.
 */

export const sddManifest = {
  flow: "sdd",
  kinds: [
    { kind: "proposal" },
    { kind: "spec" },
    { kind: "design" },
    { kind: "task" },
    { kind: "test" },
  ],
  harnessTriggers: ["always", "on_spec", "on_apply", "on_verify", "on_archive"],
  // Ordered lifecycle phases (web-ui-design-alignment, flow-registry delta
  // REQ-007): server-side data only — `init` does not generate files from
  // this field, so golden template output stays byte-identical.
  lifecycle: [
    { name: "Propose", kinds: ["proposal"] },
    { name: "Spec", kinds: ["spec", "test"] },
    { name: "Design", kinds: ["design"] },
    { name: "Tasks", kinds: ["task"] },
    { name: "Apply", kinds: ["task"] },
    { name: "Verify", kinds: ["test"] },
    { name: "Archive", kinds: ["task"] },
  ],
  skills: [
    "opensddrag-propose",
    "opensddrag-spec",
    "opensddrag-design",
    "opensddrag-tasks",
    "opensddrag-apply",
    "opensddrag-verify",
    "opensddrag-sync",
    "opensddrag-archive",
    "opensddrag-explore",
    "opensddrag-continue",
    "opensddrag-status",
    "opensddrag-flow",
    "opensddrag-search",
  ],
  commands: [
    { name: "propose", folder: "opsr" },
    { name: "spec", folder: "opsr" },
    { name: "design", folder: "opsr" },
    { name: "tasks", folder: "opsr" },
    { name: "apply", folder: "opsr" },
    { name: "verify", folder: "opsr" },
    { name: "sync", folder: "opsr" },
    { name: "archive", folder: "opsr" },
    { name: "explore", folder: "opsr" },
    { name: "continue", folder: "opsr" },
    { name: "status", folder: "opsr" },
    { name: "flow", folder: "opsr" },
    { name: "search", folder: "opsr" },
    { name: "harness", folder: "opsr" },
  ],
  claudeMdSection: `## OpenSddRag — SDD + Harness

This project uses **OpenSddRag** for Spec-Driven Development with persistent semantic memory.

- **MCP server:** configured in \`.mcp.json\`
- **Skills:** \`.claude/skills/opensddrag-*/SKILL.md\`
- **Commands:** \`.claude/commands/opsr/\`

### SDD Flow

\`\`\`
/opsr:propose → /opsr:spec → /opsr:design → /opsr:tasks → /opsr:apply → /opsr:verify → /opsr:archive
\`\`\`
`,
};

export default sddManifest;