import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
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
  language: "TypeScript",
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
    if (/\/changes\/[^/?]+/.test(url)) {
      return jsonResponse(200, {
        change: "add-stripe-billing",
        flow: "sdd",
        proposal: {
          id: "p1",
          name: "add-stripe-billing-proposal",
          type: "proposal",
          status: "draft",
          content: "# P\n\n## Why\nBill customers.",
        },
        design: null,
        specs: [],
        tasks: [],
        task_count: 0,
      });
    }
    if (url.includes("/changes")) {
      return jsonResponse(200, {
        items: [
          {
            change: "add-stripe-billing",
            flow: "sdd",
            updated_at: "2026-10-08T11:00:00Z",
            task_progress: { done: 2, total: 4 },
            phases: [
              { name: "Propose", status: "done", desc: "d" },
              { name: "Spec", status: "done", desc: "d" },
              { name: "Design", status: "done", desc: "d" },
              { name: "Tasks", status: "active", desc: "d" },
            ],
          },
        ],
        total: 1,
        page: 1,
        page_size: 8,
      });
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

// REQ-014 — detail overview, tab counts and per-change timelines (design D7)

describe("ProjectDetail overview (REQ-014)", () => {
  it("renders the header, tab counts and the paginated change list in the overview", async () => {
    renderDetail();
    expect(await screen.findByTestId("app-h1")).toBeInTheDocument();
    // tabs with counts
    expect(screen.getByRole("tab", { name: /Specs\s*2/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Tasks\s*4/i })).toBeInTheDocument();
    const card = await screen.findByTestId("change-card-add-stripe-billing");
    expect(card).toBeInTheDocument();
    expect(card).toHaveAttribute("href", "/p/demo/c/add-stripe-billing");
    expect(within(card).getByTestId("change-stage-add-stripe-billing")).toHaveTextContent("Tasks");
  });

  it("overview tab shows working context and execution traces", async () => {
    renderDetail();
    await screen.findByTestId("app-h1");
    expect(await screen.findByTestId("working-context-panel")).toBeInTheDocument();
    expect(screen.getByText("working")).toBeInTheDocument(); // the note
    expect(screen.getByTestId("traces-panel")).toBeInTheDocument();
    expect(screen.getByText(/apply_task/i)).toBeInTheDocument();
  });
});
// REQ-014 — detail header + horizontal strip (design D7, task frontend-4 unit-2)

describe("ProjectDetail header (REQ-014)", () => {
  it("shows stage chip, change line and the horizontal strip states", async () => {
    renderDetail();
    const chip = await screen.findByTestId("detail-stage-chip");
    expect(chip).toHaveTextContent("Tasks");
    const line = screen.getByTestId("header-change-line");
    expect(line).toHaveTextContent("change: add-stripe-billing · TypeScript");
    const strip = await screen.findByTestId("phase-strip-sdd");
    expect(strip).toBeInTheDocument();
    for (const phase of ["Propose", "Spec", "Design"]) {
      expect(screen.getByTestId(`strip-phase-sdd-${phase}`).dataset.state).toBe("done");
    }
    expect(screen.getByTestId("strip-phase-sdd-Tasks").dataset.state).toBe("active");
    // REQ-020 tab order: Overview, one per registered kind, Hierarchy, Harness
    const labels = screen.getAllByRole("tab").map((t) => t.textContent!.replace(/\d+$/, "").trim());
    expect(labels).toEqual(["Overview", "Proposal", "Specs", "Design", "Tasks", "Doc", "Hierarchy", "Harness"]);
  });

  it("renders no strip and keeps the tabs when there is no live change", async () => {
    const wired = wire();
    handler = (url) =>
      url.includes("/changes")
        ? jsonResponse(200, { items: [], total: 0, page: 1, page_size: 8 })
        : wired(url);
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
    await screen.findByTestId("app-h1");
    expect(screen.queryByTestId(/phase-strip-/)).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Overview/i })).toBeInTheDocument();
  });

  it("renders no strip when the active change's flow declares no lifecycle", async () => {
    const wired = wire();
    handler = (url) => {
      if (url.includes("/changes")) {
        return jsonResponse(200, {
          items: [
            {
              change: "docs-refresh",
              flow: "docs",
              updated_at: "2026-10-08T11:00:00Z",
              task_progress: { done: 0, total: 2 },
              phases: [],
            },
          ],
          total: 1,
          page: 1,
          page_size: 8,
        });
      }
      return wired(url);
    };
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
    await screen.findByTestId("app-h1");
    expect(screen.queryByTestId("phase-strip-docs")).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Overview/i })).toBeInTheDocument();
    // no timeline for the lifecycle-less change, right-column panels still render
    expect(screen.queryByTestId("phase-docs-refresh-Propose")).not.toBeInTheDocument();
    expect(await screen.findByTestId("working-context-panel")).toBeInTheDocument();
  });
});

// REQ-014 — single breadcrumb in the shell + shared getChanges fetch (task frontend-4 unit-3)

describe("ProjectDetail breadcrumb and fetches (REQ-014)", () => {
  it("renders exactly one breadcrumb (the shell's) and fetches changes once", async () => {
    const changeCalls: string[] = [];
    const wired = wire();
    handler = (url) => {
      if (url.includes("/changes")) {
        changeCalls.push(url);
      }
      return wired(url);
    };
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
    await screen.findByTestId("app-h1");
    expect(await screen.findByTestId("working-context-panel")).toBeInTheDocument();

    const breadcrumb = screen.getByTestId("app-breadcrumb");
    expect(breadcrumb.textContent).toMatch(/^projects\s*\/\s*demo$/);
    expect(screen.queryByTestId("detail-breadcrumb")).not.toBeInTheDocument();

    expect(changeCalls).toHaveLength(1);
  });
});

describe("ProjectDetail change reader (REQ-021)", () => {
  it("renders ChangeReader as the main panel on /p/:slug/c/:change", async () => {
    handler = wire();
    render(
      <RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo/c/add-stripe-billing"] })} />,
    );
    expect(await screen.findByTestId("change-reader")).toBeInTheDocument();
    expect(screen.getAllByText("Bill customers.").length).toBeGreaterThan(0);
    expect(screen.getByTestId("reader-back-overview")).toHaveAttribute("href", "/p/demo");
    expect(screen.queryByTestId("working-context-panel")).not.toBeInTheDocument();
    expect(screen.getByTestId("app-h1")).toBeInTheDocument();
  });

  it("clicking a stage shows only that stage's items, and clicking it again restores the change", async () => {
    handler = wire();
    render(
      <RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo/c/add-stripe-billing"] })} />,
    );
    expect((await screen.findAllByText("Bill customers.")).length).toBeGreaterThan(0);
    fireEvent.click(await screen.findByTestId("strip-phase-sdd-Spec"));
    expect(screen.queryAllByText("Bill customers.")).toHaveLength(0);
    expect(screen.getByText("No specs yet")).toBeInTheDocument();
    expect(screen.getByTestId("strip-phase-sdd-Spec")).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(screen.getByTestId("strip-phase-sdd-Spec"));
    expect(screen.getAllByText("Bill customers.").length).toBeGreaterThan(0);
    expect(screen.getByTestId("strip-phase-sdd-Spec")).toHaveAttribute("aria-pressed", "false");
  });
});
