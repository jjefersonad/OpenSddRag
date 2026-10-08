import PublicNav from "../../components/PublicNav";

const TOC_SECTIONS = [
  "Overview",
  "Quickstart",
  "SDD workflow",
  "Artifact formats",
  "Harness rules",
  "Agent operating rules",
  "Principles",
  "Color",
  "Typography",
  "Components",
] as const;

const SECTION_BODIES: Record<string, { heading: string; body: string[] }> = {
  Overview: {
    heading: "Overview",
    body: [
      "OpenSddRag is an MCP server with persistent semantic memory and a strict Spec-Driven Development pipeline. Every change is a named change that moves through ordered phases, each producing a versioned, embedded artifact.",
      "There are three memory layers — semantic (artifacts), episodic (execution traces), working context (sessions + harness rules). Query before you create, so you don't duplicate capabilities or reopen settled decisions.",
    ],
  },
  Quickstart: {
    heading: "Quickstart",
    body: [
      "docker compose up -d — start the database (pgvector/pg16), MCP server and web dashboard.",
      "opensddrag-server init — run migrations and seed the global SDD skills. node bin/opensddrag.js init — connect a project to the server.",
    ],
  },
  "SDD workflow": {
    heading: "SDD workflow",
    body: [
      "propose → spec → design → tasks → apply → verify → sync → archive.",
      "Run the phases in order. Each command reads the previous artifact from memory and writes the next one. Don't skip phases.",
    ],
  },
  "Artifact formats": {
    heading: "Artifact formats",
    body: [
      "proposal — ## Why, ## What Changes, ## Capabilities, ## Impact. spec — ## Requirements with #### Scenario: WHEN/THEN blocks.",
      "design — ## Decisions with chosen approach and rejected alternatives; ## Risks / Trade-offs. task — ## Goal, ## Acceptance Criteria, ## Dependencies.",
    ],
  },
  "Harness rules": {
    heading: "Harness rules",
    body: [
      "Rules are persisted per project with trigger (always/on_spec/on_apply/on_verify/on_archive) and severity (error/warning/info). Error-severity rules block the phase; warnings advise.",
      "Disable via soft-delete (enabled=false): the rule leaves default listings but can be restored.",
    ],
  },
  "Agent operating rules": {
    heading: "Agent operating rules",
    body: [
      "Read the workflow commands before acting; consult specs with semantic search before creating anything; never modify artifacts outside the phase driving them.",
    ],
  },
  Principles: {
    heading: "Principles",
    body: [
      "Query before you create. Memory is shared, not personal. Artifacts are durable decisions — traceability over convenience.",
    ],
  },
  Color: {
    heading: "Color",
    body: [
      "Backgrounds — page #0a0c0d, sidebar #0c0e10, cards #131619, insets #0e1113. Borders rgba(255,255,255,0.08).",
      "Text — primary #e8ebed, secondary #8a9298, tertiary #5b6469. Accent #10b981 (hover #34d399, on-accent #04140d). Semantic amber #fbbf24, blue #60a5fa, violet #a78bfa, red #f87171.",
    ],
  },
  Typography: {
    heading: "Typography",
    body: [
      "IBM Plex Sans for UI text (14px body, 20px page titles); IBM Plex Mono for numbers, code, labels and the ⌘K affordance. Section labels are mono 11px uppercase with 0.08em letter-spacing.",
    ],
  },
  Components: {
    heading: "Components",
    body: [
      "Card (inset background, 12px radius, 1px border) · Chip (mono 11px pill) · Section label · Phase strip (dot + label per declared lifecycle phase) · Terminal (traffic lights + mono lines) · Modal (escape closes).",
      "Accessibility: every interactive row carries aria-expanded or a role; Esc closes overlays; toggles are optimistic with rollback.",
    ],
  },
};

/** Docs & design-system page (REQ-009): sticky TOC with the agent-guide
 *  sections; public — rendered with PublicNav while logged out. */
export default function DocsPage() {
  return (
    <div style={{ minHeight: "100%", background: "var(--color-page)", color: "var(--color-text)" }}>
      <PublicNav />
      <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: "24px", maxWidth: "1180px", margin: "0 auto", padding: "32px" }}>
        <nav data-testid="docs-toc" aria-label="Docs sections" style={{ position: "sticky", top: "24px", alignSelf: "start", display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em", color: "#5b6469", marginBottom: "8px" }}>
            On this page
          </div>
          {TOC_SECTIONS.map((section) => (
            <a
              key={section}
              href={`#docs-${slugify(section)}`}
              style={{ color: "var(--color-text-secondary)", fontSize: "13.5px", textDecoration: "none" }}
            >
              {section}
            </a>
          ))}
        </nav>

        <main style={{ display: "flex", flexDirection: "column", gap: "40px" }}>
          <div>
            <h1 style={{ margin: "0 0 12px", fontSize: "24px" }}>Docs &amp; design system</h1>
            <p style={{ color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
              The agent guide and the §8 design-system reference, mirrored from{" "}
              <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>docs/ui/AGENT_GUIDE.md</code>.
            </p>
          </div>
          {TOC_SECTIONS.map((section) => {
            const body = SECTION_BODIES[section];
            return (
              <section
                key={section}
                id={`docs-${slugify(section)}`}
                data-testid={`docs-section-${slugify(section)}`}
                style={{ scrollMarginTop: "80px" }}
              >
                <h2 style={{ margin: "0 0 12px", fontSize: "17px" }}>{section}</h2>
                {body?.body.map((paragraph, i) => (
                  <p key={i} style={{ color: "var(--color-text-secondary)", lineHeight: 1.65, fontSize: "14px", margin: "0 0 12px", textWrap: "pretty" }}>
                    {paragraph}
                  </p>
                ))}
              </section>
            );
          })}
        </main>
      </div>
    </div>
  );
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}