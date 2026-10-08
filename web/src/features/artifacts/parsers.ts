import type { Artifact } from "../../api/types";

/**
 * Tolerant markdown parsers for structural artifact rendering (REQ-015 +
 * tests-1 unit-1 contract). All parsers are pure functions; given malformed
 * content they return empty values (never throw), and renderers fall back
 * to raw text.
 */

/** Extract the text under each `## Heading` named in `wanted` (case-insensitive). */
export function parseSections(content: string, wanted: string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const name of wanted) out[name] = "";
  const lines = (content ?? "").split("\n");
  let current: string | null = null;
  for (const line of lines) {
    const match = /^##\s+(.*)$/.exec(line.trim());
    if (match) {
      const title = match[1].trim();
      const key = wanted.find((w) => w.toLowerCase() === title.toLowerCase());
      current = key ?? null;
      continue;
    }
    if (current && /^#{1,6}\s/.test(line.trim())) {
      // nested heading ends the section only if it is another `##` level
      const nested = /^##\s+(.*)$/.exec(line.trim());
      if (nested) {
        const nestedKey = wanted.find((w) => w.toLowerCase() === nested[1].trim().toLowerCase());
        current = nestedKey ?? null;
        continue;
      }
    }
    if (current) out[current] += (out[current] ? "\n" : "") + line;
  }
  for (const key of Object.keys(out)) out[key] = out[key].trim();
  return out;
}

export interface ParsedScenario {
  name: string;
  when: string;
  then: string;
}

export interface ParsedRequirement {
  id: string;
  title: string;
  shall: string;
  scenarios: ParsedScenario[];
}

/** Extract `### Requirement: REQ-NNN ...` blocks with SHALL + WHEN/THEN scenarios. */
export function parseRequirements(content: string): ParsedRequirement[] {
  const lines = (content ?? "").split("\n");
  const reqs: ParsedRequirement[] = [];
  let current: ParsedRequirement | null = null;
  let scenario: ParsedScenario | null = null;
  let mode: "shall" | "scenario-body" | null = null;

  for (const raw of lines) {
    const line = raw.trim();
    const reqMatch = /^###\s+Requirement:\s*(.+)$/.exec(line);
    if (reqMatch) {
      if (current) reqs.push(current);
      const heading = reqMatch[1].trim();
      const idMatch = /^(REQ-\d+)\s*(.*)$/.exec(heading);
      current = {
        id: idMatch ? idMatch[1] : heading,
        title: idMatch ? idMatch[2].trim() : heading,
        shall: "",
        scenarios: [],
      };
      mode = null;
      continue;
    }
    if (!current) continue;

    const scenarioMatch = /^####\s+Scenario:\s*(.+)$/.exec(line);
    if (scenarioMatch) {
      scenario = { name: scenarioMatch[1].trim(), when: "", then: "" };
      current.scenarios.push(scenario);
      mode = "scenario-body";
      continue;
    }

    if (!scenario) {
      // Requirement body — the SHALL sentence(s)
      if (/shall|must/i.test(line) && line && !line.startsWith("#")) {
        current.shall += (current.shall ? " " : "") + line;
        mode = "shall";
      } else if (mode === "shall" && line && !line.startsWith("#")) {
        current.shall += " " + line;
      } else if (line.startsWith("#") || line === "") {
        if (line.startsWith("#")) mode = null;
      }
      continue;
    }
    if (mode === "scenario-body" && /^[-*]\s+\*\*WHEN\*\*/i.test(line)) {
      scenario.when = bulletText(line);
    } else if (mode === "scenario-body" && /^[-*]\s+\*\*THEN\*\*/i.test(line)) {
      scenario.then = bulletText(line);
      mode = null;
    }
  }
  if (current) reqs.push(current);
  return reqs;
}

function bulletText(line: string): string {
  return line.replace(/^[-*]\s+\*\*(WHEN|THEN)\*\*\s*/i, "").trim();
}

/** Extract design `### Decision:` blocks and the risks table rows. */
export function parseDesignSections(content: string): { decisions: string[]; risks: string[] } {
  const decisions: string[] = [];
  const risks: string[] = [];
  let current: "decisions" | "risks" | null = null;
  for (const raw of (content ?? "").split("\n")) {
    const line = raw.trim();
    if (/^##\s+Decisions/i.test(line) || /^##\s+Technical decisions/i.test(line)) {
      current = "decisions";
      continue;
    }
    if (/^##\s+Risks/i.test(line)) {
      current = "risks";
      continue;
    }
    if (/^##\s/.test(line) && current) {
      current = null;
      continue;
    }
    if (current === "decisions" && /^###\s+Decision:/i.test(line)) {
      decisions.push(line.replace(/^###\s+Decision:\s*/i, ""));
    }
    if (current === "decisions" && line.startsWith("**Chosen:**")) {
      decisions.push(line.replace(/^\*\*Chosen:\*\*\s*/, ""));
    }
    if (current === "risks" && line.startsWith("|") && !/^\|\s*-/.test(line) && !/\| Risk \|/.test(line)) {
      const cells = line.split("|").map((c) => c.trim()).filter(Boolean);
      if (cells.length >= 1) risks.push(cells.join(" — "));
    }
  }
  return { decisions, risks };
}

/** Structured renderer dispatch — known kinds vs generic fallback. */
export const STRUCTURED_KINDS = new Set(["proposal", "spec", "design", "task"]);

export function hasStructuredRenderer(kind: string): boolean {
  return STRUCTURED_KINDS.has(kind);
}

export function artifactFlow(artifact: Artifact): string {
  return artifact.flow ?? "sdd";
}