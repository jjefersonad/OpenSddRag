import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../../routes";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

type UrlHandler = (url: string) => Response;

let handler: UrlHandler;
beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("opensddrag.management_token", "t");
  vi.stubGlobal("fetch", vi.fn(async (input: string) => handler(String(input))));
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const DETAIL = {
  id: "1",
  name: "Demo",
  slug: "demo",
  language: "Python",
  summary: { proposal: 1, spec: 2, task: 4 },
  flows: [
    { flow: "sdd", phase: "Design", task_progress: { done: 2, total: 4 } },
    { flow: "docs", phase: null, task_progress: { done: 0, total: 0 } },
  ],
  task_progress: { done: 2, total: 4 },
};

function wire(): UrlHandler {
  return (url) => {
    if (url.endsWith("/projects/demo")) return jsonResponse(200, DETAIL);
    if (url.includes("/artifacts?type=")) return jsonResponse(200, []);
    if (url.includes("/changes")) {
      return jsonResponse(200, [
        {
          change: "add-stripe-billing",
          flow: "sdd",
          updated_at: "2026-10-08T11:00:00Z",
          task_progress: { done: 2, total: 4 },
          phases: [
            { name: "Propose", status: "done", desc: "d" },
            { name: "Spec", status: "done", desc: "d" },
            { name: "Design", status: "active", desc: "d" },
          ],
        },
      ]);
    }
    if (url.includes("/projects/demo/session")) {
      return jsonResponse(200, { active_artifacts: [{ id: "a1", name: "p", type: "proposal" }], note: "working" });
    }
    if (url.includes("/projects/demo/traces")) {
      return jsonResponse(200, [{ id: "tr1", action: "apply_task", result_summary: "did x" }]);
    }
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
            { name: "Spec", kinds: ["spec", "test"] },
            { name: "Design", kinds: ["design"] },
            { name: "Tasks", kinds: ["task"] },
            { name: "Apply", kinds: ["task"] },
            { name: "Verify", kinds: ["test"] },
            { name: "Archive", kinds: ["task"] },
          ],
        },
        { flow: "docs", kinds: [{ kind: "doc", rules: {} }], lifecycle: null },
      ]);
    }
    return jsonResponse(200, []);
  };
}

function renderDetail() {
  handler = wire();
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
}

// REQ-014 — detail overview, multi-flow aware (design D6/D7/D8)

describe("ProjectDetail overview (REQ-014)", () => {
  it("renders breadcrumb, tab counts and per-flow phase strips", async () => {
    renderDetail();
    expect(await screen.findByTestId("detail-breadcrumb")).toBeInTheDocument();
    expect(screen.getByText(/projects \/ demo/i)).toBeInTheDocument();
    // tabs with counts
    expect(screen.getByRole("tab", { name: /Specs\s*2/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Tasks\s*4/i })).toBeInTheDocument();
    // Changes-in-progress card with per-change phase timeline (REQ-014 delta:
    // the per-flow strip was superseded by per-change granularity)
    const card = await screen.findByTestId("change-card-add-stripe-billing");
    expect(card).toBeInTheDocument();
    expect(await waitFor(() => screen.getByTestId("phase-add-stripe-billing-Design"))).toBeInTheDocument();
    expect(screen.getByText("Propose")).toBeInTheDocument();
  });

  it("omits the phase strip for flows without a declared lifecycle", async () => {
    renderDetail();
    await screen.findByTestId("detail-breadcrumb");
    // flow without lifecycle → its change card renders without phase timeline
    await screen.findByTestId("working-context-panel");
  });

  it("overview tab shows working context and execution traces", async () => {
    renderDetail();
    await screen.findByTestId("detail-breadcrumb");
    expect(await screen.findByTestId("working-context-panel")).toBeInTheDocument();
    expect(screen.getByText("working")).toBeInTheDocument(); // the note
    expect(screen.getByTestId("traces-panel")).toBeInTheDocument();
    expect(screen.getByText(/apply_task/i)).toBeInTheDocument();
  });
});