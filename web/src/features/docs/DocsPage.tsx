import { type ComponentType } from "react";
import PublicNav from "../../components/PublicNav";
import { DESIGN_TOKENS, TYPE_SCALE, type TypeScaleSample } from "./designTokens";
import { TOC_SECTIONS, slugify, type DocsSection } from "./docsToc";
import {
  ApiKeysBody,
  ClaudeCodeBody,
  CliClientBody,
  DashboardBody,
  OpenCodeBody,
  PipelinesBody,
  QuickstartBody,
  ServerSetupBody,
  HarnessBody,
} from "./gettingStarted";

const SECTION_BODIES: Partial<Record<DocsSection, string[]>> = {
  Overview: [
    "OpenSddRag is an MCP server with persistent semantic memory. SDD is the built-in pipeline: a named change moves through ordered phases, each producing a versioned, embedded artifact. You can register extra pipelines (flows) with their own kinds and lifecycle.",
    "There are three memory layers — semantic (artifacts), episodic (execution traces), working context (sessions + harness rules). Query before you create, so you don't duplicate capabilities or reopen settled decisions.",
    "This page is the getting-started guide: stand up the server, connect the CLI, wire Claude Code, Cursor and OpenCode, then pipelines (SDD is the built-in one — others declare their own phases and artifact kinds) and the design-system tokens.",
  ],
  "Harness rules": [
    "Rules are persisted per project with a trigger, category, severity and a plain-language instruction. Error-severity rules block the gate; warnings advise. Disable via soft-delete (enabled=false).",
  ],
  "Agent operating rules": [
    "Read the active pipeline's commands before acting. Search semantic memory before creating artifacts so you do not duplicate work or reopen settled decisions. Never modify artifacts outside the phase that owns them. Follow always-injected harness rules at session start.",
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

/** Docs page: getting-started (server, CLI, Claude Code, OpenCode) plus the
 *  agent-guide sections and the §8 design-system reference. Public. */
export default function DocsPage() {
  return (
    <div style={{ minHeight: "100%", background: "var(--color-page)", color: "var(--color-text)" }}>
      <PublicNav />
      <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: "24px", maxWidth: "1180px", margin: "0 auto", padding: "32px" }}>
        <nav data-testid="docs-toc" aria-label="Docs sections" style={{ position: "sticky", top: "24px", alignSelf: "start", display: "flex", flexDirection: "column", gap: "6px", maxHeight: "calc(100vh - 48px)", overflowY: "auto" }}>
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
            <h1 style={{ margin: "0 0 12px", fontSize: "24px" }}>Docs</h1>
            <p style={{ color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
              Set up the server, connect a project with the CLI, wire Claude Code, Cursor and OpenCode, then pipelines
              (including the built-in SDD flow) and design-system tokens.
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
  "Server setup": ServerSetupBody,
  Dashboard: DashboardBody,
  "CLI client": CliClientBody,
  "Claude Code": ClaudeCodeBody,
  OpenCode: OpenCodeBody,
  "API keys": ApiKeysBody,
  Pipelines: PipelinesBody,
  "Harness rules": HarnessBody,
  Color: ColorSwatches,
  Typography: TypeSamples,
  Components: ComponentSamples,
};

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
