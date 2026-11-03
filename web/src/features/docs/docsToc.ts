/** Ordered TOC for `/docs`. Shared by DocsPage and its tests. */
export const TOC_SECTIONS = [
  "Overview",
  "Quickstart",
  "Server setup",
  "Dashboard",
  "CLI client",
  "Claude Code",
  "OpenCode",
  "API keys",
  "Pipelines",
  "Harness rules",
  "Agent operating rules",
  "Principles",
  "Color",
  "Typography",
  "Components",
] as const;

export type DocsSection = (typeof TOC_SECTIONS)[number];

export function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}
