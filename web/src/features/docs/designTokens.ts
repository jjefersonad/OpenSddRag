// Design tokens for the docs design-system reference (design D10, REQ-009).
// Source of truth: web/src/styles/tokens.css — a drift-guard test fails if a
// value here is edited in one place only.

export type DesignToken = {
  name: string;
  cssVar: string;
  hex: string;
  usage: string;
};

export type TypeScaleSample = {
  id: "sans" | "mono";
  label: string;
  fontFamily: string;
  size: string;
  sample: string;
  uppercase?: boolean;
};

export const DESIGN_TOKENS: DesignToken[] = [
  { name: "Page background", cssVar: "--color-page", hex: "#0a0c0d", usage: "App and docs page backdrop" },
  { name: "Sidebar", cssVar: "--color-sidebar", hex: "#0c0e10", usage: "Top nav and sidebars" },
  { name: "Card", cssVar: "--color-card", hex: "#131619", usage: "List cards and modals" },
  { name: "Inset", cssVar: "--color-inset", hex: "#0e1113", usage: "Code blocks and wells inside cards" },
  { name: "Border", cssVar: "--color-border", hex: "rgba(255, 255, 255, 0.08)", usage: "Hairline borders on cards and rows" },
  { name: "Text primary", cssVar: "--color-text-primary", hex: "#e8ebed", usage: "Headings and body text" },
  { name: "Text secondary", cssVar: "--color-text-secondary", hex: "#8a9298", usage: "Supporting copy" },
  { name: "Text tertiary", cssVar: "--color-text-tertiary", hex: "#5b6469", usage: "Section labels and metadata" },
  { name: "Accent", cssVar: "--color-accent", hex: "#10b981", usage: "Primary actions and active states" },
  { name: "Accent hover", cssVar: "--color-accent-hover", hex: "#34d399", usage: "Hover state of primary actions" },
  { name: "On accent", cssVar: "--color-on-accent", hex: "#04140d", usage: "Text on accent surfaces" },
  { name: "Warn amber", cssVar: "--color-warn", hex: "#fbbf24", usage: "amber — WHEN / warning / proposal" },
  { name: "Info blue", cssVar: "--color-info", hex: "#60a5fa", usage: "blue — SHALL / info / spec" },
  { name: "Design violet", cssVar: "--color-design", hex: "#a78bfa", usage: "violet — design" },
  { name: "Danger red", cssVar: "--color-danger", hex: "#f87171", usage: "red — error / risk" },
];

export const TYPE_SCALE: TypeScaleSample[] = [
  {
    id: "sans",
    label: "Page title",
    fontFamily: "var(--font-sans)",
    size: "20px",
    sample: "Docs & design system",
  },
  {
    id: "sans",
    label: "Body",
    fontFamily: "var(--font-sans)",
    size: "14px",
    sample: "Every change is a named change that moves through ordered phases.",
  },
  {
    id: "mono",
    label: "Section label",
    fontFamily: "var(--font-mono)",
    size: "11px",
    sample: "On this page",
    uppercase: true,
  },
  {
    id: "mono",
    label: "Mono metadata",
    fontFamily: "var(--font-mono)",
    size: "12px",
    sample: "opensddrag/spec-001",
  },
];