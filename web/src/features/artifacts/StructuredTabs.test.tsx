import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../../routes";
import { parseSections, parseRequirements, parseDesignSections } from "./parsers";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

type UrlHandler = (url: string) => Response;
let handler: UrlHandler;
const DETAIL = {
  id: "1",
  name: "Demo",
  slug: "demo",
  summary: { proposal: 1, spec: 1, design: 1, task: 1, "meeting-note": 1 },
  flows: [
    { flow: "sdd", phase: "Design", task_progress: { done: 0, total: 1 } },
    { flow: "meetings", phase: null, task_progress: { done: 0, total: 0 } },
  ],
  task_progress: { done: 0, total: 1 },
};

const PROPOSAL_CONTENT = [
  "# change-x",
  "",
  "## Why",
  "The problem is X.",
  "",
  "## What Changes",
  "- Add Y.",
  "",
  "## Capabilities",
  "",
  "### Modified Capabilities",
  "- **alpha** — changes Z.",
  "",
  "## Impact",
  "- Some impact.",
].join("\n");

const SPEC_CONTENT = [
  "# alpha Specification",
  "",
  "## Requirements",
  "",
  "### Requirement: REQ-001 Do the thing",
  "The system SHALL do the thing.",
  "",
  "#### Scenario: Happy path",
  "- **WHEN** invoked",
  "- **THEN** it happens",
].join("\n");

const DESIGN_CONTENT = [
  "# Design: change-x",
  "",
  "## Decisions",
  "",
  "### Decision: Use D6 lifecycle",
  "**Chosen:** declarative phases.",
  "",
  "## Risks / Trade-offs",
  "",
  "| Risk | Mitigation |",
  "|------|------------|",
  "| r1 | m1 |",
].join("\n");

const MEETING_CONTENT = "# meeting-note\n\n## Attendees\n\n- jeff";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("opensddrag.management_token", "t");
  handler = (url) => {
    if (url.endsWith("/projects/demo")) return jsonResponse(200, DETAIL);
    if (url.includes("type=proposal")) return jsonResponse(200, [artifact("p1", "change-x-proposal", "proposal", PROPOSAL_CONTENT, "sdd")]);
    if (url.includes("type=spec")) return jsonResponse(200, [artifact("s1", "alpha-spec", "spec", SPEC_CONTENT, "sdd")]);
    if (url.includes("type=design")) return jsonResponse(200, [artifact("d1", "change-x-design", "design", DESIGN_CONTENT, "sdd")]);
    if (url.includes("type=task")) return jsonResponse(200, [artifact("t1", "task-1", "task", "## Goal\nDo it.", "sdd", { done: false })]);
    if (url.includes("type=meeting-note")) return jsonResponse(200, [artifact("m1", "weekly", "meeting-note", MEETING_CONTENT, "meetings")]);
    if (url.includes("/session")) return jsonResponse(200, { active_artifacts: [], note: null });
    if (url.includes("/traces")) return jsonResponse(200, []);
    if (url.endsWith("/flows")) {
      return jsonResponse(200, [
        {
          flow: "sdd",
          kinds: [
            { kind: "proposal", rules: {} },
            { kind: "spec", rules: {} },
            { kind: "design", rules: {} },
            { kind: "task", rules: {} },
          ],
          lifecycle: [
            { name: "Propose", kinds: ["proposal"] },
            { name: "Spec", kinds: ["spec"] },
            { name: "Design", kinds: ["design"] },
            { name: "Tasks", kinds: ["task"] },
            { name: "Archive", kinds: ["task"] },
          ],
        },
        {
          flow: "meetings",
          kinds: [{ kind: "meeting-note", rules: {} }],
          lifecycle: null,
        },
      ]);
    }
    return jsonResponse(200, []);
  };
  vi.stubGlobal("fetch", vi.fn(async (input: string) => handler(String(input))));
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function artifact(id: string, name: string, type: string, content: string, flow: string, metadata: Record<string, unknown> = {}) {
  return { id, name, type, status: "draft", content, flow, metadata };
}

function renderDetail() {
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
}

// REQ-015 — structured renderers

describe("Structured artifact tabs (REQ-015)", () => {
  it("Specs tab renders SHALL text with expandable WHEN/THEN", async () => {
    renderDetail();
    fireEvent.click(await screen.findByRole("tab", { name: /Specs\s*1/i }));
    const card = await screen.findByText("The system SHALL do the thing.");
    expect(card).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Happy path/i }));
    expect(await screen.findByText(/WHEN.*invoked/i)).toBeInTheDocument();
    expect(screen.getByText(/THEN.*it happens/i)).toBeInTheDocument();
  });

  it("unknown kind falls back to the generic renderer without error", async () => {
    renderDetail();
    fireEvent.click(await screen.findByRole("tab", { name: /meeting-note\s*1/i }));
    expect(await screen.findByTestId("generic-artifact-weekly")).toBeInTheDocument();
    expect(screen.getByText(/Attendees/i)).toBeInTheDocument();
  });

  it("task checkbox toggles optimistically and reverts on failure", async () => {
    handler = (url) => {
      if (url.endsWith("/projects/demo")) return jsonResponse(200, DETAIL);
      if (url.includes("type=task")) {
        return jsonResponse(200, [artifact("t1", "task-1", "task", "## Goal\nDo it.", "sdd", { done: false })]);
      }
      if (url.includes("/session")) return jsonResponse(200, { active_artifacts: [], note: null });
      if (url.includes("/traces")) return jsonResponse(200, []);
      if (url.endsWith("/flows")) {
        return jsonResponse(200, [{ flow: "sdd", kinds: [{ kind: "task", rules: {} }], lifecycle: null }]);
      }
      return jsonResponse(200, []);
    };
    renderDetail();
    fireEvent.click(await screen.findByRole("tab", { name: /Tasks\s*1/i }));
    await screen.findByRole("checkbox", { name: /toggle task-1/i });
    const checkbox = (await screen.findByRole("checkbox", { name: /toggle task-1/i })) as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
    // failing PATCH
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string) => {
        const url = String(input);
        if (url.includes("/tasks/t1")) return jsonResponse(500, { error: { code: "INTERNAL" } });
        if (url.includes("type=task")) return jsonResponse(200, [artifact("t1", "task-1", "task", "g", "sdd", { done: false })]);
        return jsonResponse(200, []);
      }),
    );
    fireEvent.click(checkbox);
    // optimistic update applied first...
    expect(checkbox.checked).toBe(true);
    // ...then rollback shows the error
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect((screen.getByRole("checkbox", { name: /toggle task-1/i }) as HTMLInputElement).checked).toBe(false);
  });
});

// parsers (tolerant, tests-1's unit-1 contract asserted early here)

describe("artifact parsers", () => {
  it("parseSections extracts headings sections with raw fallback", () => {
    const sections = parseSections(PROPOSAL_CONTENT, ["Why", "What Changes"]);
    expect(sections["Why"]).toContain("The problem is X.");
    expect(sections["What Changes"]).toContain("Add Y.");
    expect(parseSections("", ["Why"])["Why"]).toBe("");
  });

  it("parseRequirements extracts SHALL + WHEN/THEN scenarios", () => {
    const reqs = parseRequirements(SPEC_CONTENT);
    expect(reqs).toHaveLength(1);
    expect(reqs[0].id).toBe("REQ-001");
    expect(reqs[0].shall).toContain("SHALL do the thing");
    expect(reqs[0].scenarios).toHaveLength(1);
    expect(reqs[0].scenarios[0]).toHaveProperty("when");
  });

  it("parseDesignSections extracts decisions/risks", () => {
    const parsed = parseDesignSections(DESIGN_CONTENT);
    expect(parsed.decisions.join("\n")).toContain("D6 lifecycle");
    expect(parsed.risks.join("\n")).toContain("r1");
  });
});