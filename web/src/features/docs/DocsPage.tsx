import { type ComponentType, type CSSProperties } from "react";
import PublicNav from "../../components/PublicNav";
import { DESIGN_TOKENS, TYPE_SCALE, type TypeScaleSample } from "./designTokens";

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

type DocsSection = (typeof TOC_SECTIONS)[number];

const SECTION_BODIES: Partial<Record<DocsSection, string[]>> = {
  Overview: [
    "OpenSddRag is an MCP server with persistent semantic memory and a strict Spec-Driven Development pipeline. Every change is a named change that moves through ordered phases, each producing a versioned, embedded artifact.",
    "There are three memory layers — semantic (artifacts), episodic (execution traces), working context (sessions + harness rules). Query before you create, so you don't duplicate capabilities or reopen settled decisions.",
  ],
  "SDD workflow": [
    "propose → spec → design → tasks → apply → verify → sync → archive.",
    "Run the phases in order. Each command reads the previous artifact from memory and writes the next one. Don't skip phases.",
  ],
  "Artifact formats": [
    "proposal — ## Why, ## What Changes, ## Capabilities, ## Impact. spec — ## Requirements with #### Scenario: WHEN/THEN blocks.",
    "design — ## Decisions with chosen approach and rejected alternatives; ## Risks / Trade-offs. task — ## Goal, ## Acceptance Criteria, ## Dependencies.",
  ],
  "Harness rules": [
    "Rules are persisted per project with trigger (always/on_spec/on_apply/on_verify/on_archive) and severity (error/warning/info). Error-severity rules block the phase; warnings advise.",
    "Disable via soft-delete (enabled=false): the rule leaves default listings but can be restored.",
  ],
  "Agent operating rules": [
    "Read the workflow commands before acting; consult specs with semantic search before creating anything; never modify artifacts outside the phase driving them.",
  ],
  Principles: [
    "Query before you create. Memory is shared, not personal. Artifacts are durable decisions — traceability over convenience.",
  ],
  Color: [
    "Backgrounds — page #0a0c0d, sidebar #0c0e10, cards #131619, insets #0e1113. Borders rgba(255,255,255,0.08).",
    "Text — primary #e8ebed, secondary #8a9298, tertiary #5b6469. Accent #10b981 (hover #34d399, on-accent #04140d). Semantic amber #fbbf24, blue #60a5fa, violet #a78bfa, red #f87171.",
  ],
  Typography: [
    "IBM Plex Sans for UI text (14px body, 20px page titles); IBM Plex Mono for numbers, code, labels and the ⌘K affordance. Section labels are mono 11px uppercase with 0.08em letter-spacing.",
  ],
  Components: [
    "Card (inset background, 12px radius, 1px border) · Chip (mono 11px pill) · Section label · Phase strip (dot + label per declared lifecycle phase) · Terminal (traffic lights + mono lines) · Modal (escape closes).",
    "Accessibility: every interactive row carries aria-expanded or a role; Esc closes overlays; toggles are optimistic with rollback.",
  ],
};

const QUICKSTART_COMMANDS = [
  {
    command: "docker compose up -d",
    description: "Start the database (pgvector/pg16), MCP server and web dashboard.",
  },
  {
    command: "opensddrag-server init",
    description: "Run migrations and seed the global SDD skills.",
  },
  {
    command: "node bin/opensddrag.js init",
    description: "Connect a project to the server.",
  },
];

const SEVERITY_SAMPLES = [
  { name: "error", color: "var(--color-danger)", background: "rgba(248, 113, 113, 0.1)", borderColor: "rgba(248, 113, 113, 0.25)" },
  { name: "warning", color: "var(--color-warn)", background: "rgba(251, 191, 36, 0.1)", borderColor: "rgba(251, 191, 36, 0.25)" },
  { name: "info", color: "var(--color-info)", background: "rgba(96, 165, 250, 0.1)", borderColor: "rgba(96, 165, 250, 0.25)" },
] as const;

const PHASE_SAMPLES = [
  { label: "propose", dotColor: "var(--color-accent)" },
  { label: "spec", dotColor: "var(--color-info)" },
  { label: "apply", dotColor: "var(--color-warn)" },
  { label: "review", dotColor: "var(--color-design)" },
  { label: "archive", dotColor: "var(--color-text-tertiary)" },
] as const;

const CODE_BLOCK_STYLE: CSSProperties = {
  margin: 0,
  padding: "10px 12px",
  fontFamily: "var(--font-mono)",
  fontSize: "12px",
  color: "var(--color-text-primary)",
  background: "var(--color-inset)",
  border: "1px solid var(--color-border)",
  borderRadius: "8px",
  overflowX: "auto",
};

/** Docs & design-system page (REQ-009): sticky TOC with the agent-guide
 *  sections plus the §8 design-system reference — color swatches, type scale
 *  samples and live component samples driven by designTokens.ts. Public. */
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
          {TOC_SECTIONS.map((section) => (
            <section
              key={section}
              id={`docs-${slugify(section)}`}
              data-testid={`docs-section-${slugify(section)}`}
              style={{ scrollMarginTop: "80px" }}
            >
              <h2 style={{ margin: "0 0 12px", fontSize: "17px" }}>{section}</h2>
              <SectionBody section={section} />
            </section>
          ))}
        </main>
      </div>
    </div>
  );
}

/** Prose paragraphs plus (for the design-system sections) the live samples. */
function SectionBody({ section }: { section: DocsSection }) {
  const Extra = SECTION_EXTRAS[section];
  return (
    <>
      {(SECTION_BODIES[section] ?? []).map((paragraph, i) => (
        <p key={i} style={{ color: "var(--color-text-secondary)", lineHeight: 1.65, fontSize: "14px", margin: "0 0 12px", textWrap: "pretty" }}>
          {paragraph}
        </p>
      ))}
      {Extra ? <Extra /> : null}
    </>
  );
}

const SECTION_EXTRAS: Partial<Record<DocsSection, ComponentType>> = {
  Quickstart: QuickstartBody,
  Color: ColorSwatches,
  Typography: TypeSamples,
  Components: ComponentSamples,
};

function QuickstartBody() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      {QUICKSTART_COMMANDS.map((entry) => (
        <div key={entry.command} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <pre style={CODE_BLOCK_STYLE}>
            <code style={{ fontFamily: "var(--font-mono)" }}>{entry.command}</code>
          </pre>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "13.5px", lineHeight: 1.5, margin: 0 }}>
            {entry.description}
          </p>
        </div>
      ))}
    </div>
  );
}

function ColorSwatches() {
  return (
    <div style={{ marginTop: "14px", display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "10px" }}>
      {DESIGN_TOKENS.map((token) => (
        <div
          key={token.cssVar}
          data-testid={`docs-swatch-${slugify(token.name)}`}
          title={token.usage}
          style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px", background: "var(--color-inset)", border: "1px solid var(--color-border)", borderRadius: "10px" }}
        >
          <span
            aria-hidden="true"
            data-hex={token.hex}
            style={{ width: "20px", height: "20px", borderRadius: "6px", flexShrink: 0, background: token.hex, border: token.hex.startsWith("rgba(") ? "1px dashed rgba(255, 255, 255, 0.25)" : "none" }}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: "2px", minWidth: 0 }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-text-primary)" }}>{token.name}</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--color-text-tertiary)" }}>{token.hex}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/** The first sample of each family carries the docs-type-sans / docs-type-mono
 *  test id; the remaining samples of the same family render unmarked. */
function representativeTypeSample(sample: TypeScaleSample): boolean {
  return TYPE_SCALE.find((entry) => entry.id === sample.id) === sample;
}

function TypeSamples() {
  return (
    <div style={{ marginTop: "14px", display: "flex", flexDirection: "column", gap: "8px", padding: "14px", background: "var(--color-inset)", border: "1px solid var(--color-border)", borderRadius: "10px" }}>
      {TYPE_SCALE.map((entry) => (
        <div
          key={entry.label}
          data-testid={representativeTypeSample(entry) ? `docs-type-${entry.id}` : undefined}
          style={{ display: "flex", alignItems: "baseline", gap: "10px", fontFamily: entry.fontFamily, fontSize: entry.size, color: "var(--color-text-primary)", textTransform: entry.uppercase ? "uppercase" : undefined, letterSpacing: entry.uppercase ? "0.08em" : undefined }}
        >
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--color-text-tertiary)", letterSpacing: "0.08em", textTransform: "uppercase", flexShrink: 0 }}>
            {entry.label} · {entry.size}
          </span>
          <span>{entry.sample}</span>
        </div>
      ))}
    </div>
  );
}

function MonoChip(props: { testId: string; label: string; color: string; background: string; borderColor: string }) {
  return (
    <span
      data-testid={props.testId}
      style={{ display: "inline-block", fontFamily: "var(--font-mono)", fontSize: "11px", lineHeight: 1.4, color: props.color, background: props.background, border: `1px solid ${props.borderColor}`, borderRadius: "999px", padding: "2px 10px" }}
    >
      {props.label}
    </span>
  );
}

function ComponentSamples() {
  return (
    <div style={{ marginTop: "14px", display: "flex", flexDirection: "column", gap: "14px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
        <button
          data-testid="docs-sample-button"
          type="button"
          style={{ background: "var(--color-accent)", color: "var(--color-on-accent)", fontFamily: "var(--font-sans)", fontSize: "13px", fontWeight: 600, border: "none", borderRadius: "8px", padding: "8px 14px", cursor: "pointer" }}
        >
          Primary action
        </button>
        <MonoChip testId="docs-sample-stage-chip" label="apply" color="var(--color-accent-hover)" background="rgba(16, 185, 129, 0.1)" borderColor="rgba(16, 185, 129, 0.25)" />
        {SEVERITY_SAMPLES.map((severity) => (
          <MonoChip
            key={severity.name}
            testId={`docs-sample-severity-${severity.name}`}
            label={severity.name}
            color={severity.color}
            background={severity.background}
            borderColor={severity.borderColor}
          />
        ))}
      </div>
      <div data-testid="docs-sample-card" style={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: "12px", padding: "14px", display: "flex", flexDirection: "column", gap: "6px" }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--color-text-tertiary)" }}>Card</span>
        <span style={{ fontSize: "13.5px", lineHeight: 1.5, color: "var(--color-text-secondary)" }}>
          Card-tinted container with a 12px radius and 1px hairline border — every list row lives in one.
        </span>
      </div>
      <div data-testid="docs-sample-phase-strip" style={{ display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap", padding: "10px 12px", background: "var(--color-inset)", border: "1px solid var(--color-border)", borderRadius: "10px" }}>
        {PHASE_SAMPLES.map((phase) => (
          <span key={phase.label} style={{ display: "flex", alignItems: "center", gap: "6px", fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--color-text-secondary)" }}>
            <span data-dot="true" style={{ width: "8px", height: "8px", borderRadius: "999px", background: phase.dotColor }} />
            {phase.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}