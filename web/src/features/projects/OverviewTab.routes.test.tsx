import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../../routes";
import type { ChangeSummary } from "../../api/changes";
import type { SessionSummary } from "../../api/session";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}
const CHANGES: ChangeSummary[] = [
  {
    change: "chg-one",
    flow: "sdd",
    updated_at: "2026-10-08T11:00:00Z",
    task_progress: { done: 0, total: 1 },
    phases: [
      { name: "Propose", status: "done", desc: "Define what & why — problem, changes, affected capabilities." },
      { name: "Spec", status: "done", desc: "Testable requirements with WHEN/THEN scenarios." },
      { name: "Design", status: "done", desc: "Technical decisions, trade-offs, risks." },
      { name: "Tasks", status: "active", desc: "Break the design into trackable tasks." },
      { name: "Apply", status: "pending", desc: "Implement tasks, marking [ ] → [x]." },
      { name: "Verify", status: "pending", desc: "Validate spec scenarios against the code." },
      { name: "Sync", status: "pending", desc: "Merge delta specs back into the base." },
      { name: "Archive", status: "pending", desc: "Close the change, record in history." },
    ],
  },
  {
    change: "chg-two",
    flow: "sdd",
    updated_at: "2026-10-08T10:00:00Z",
    task_progress: { done: 0, total: 0 },
    phases: [
      { name: "Propose", status: "active", desc: "Define what & why — problem, changes, affected capabilities." },
      { name: "Spec", status: "pending", desc: "Testable requirements with WHEN/THEN scenarios." },
    ],
  },
];

const ONE_CHANGE: ChangeSummary[] = [CHANGES[0]];

const BARE_CHANGE: ChangeSummary = {
  change: "chg-bare",
  flow: "sdd",
  updated_at: "2026-10-08T09:00:00Z",
  task_progress: { done: 1, total: 2 },
  phases: [],
};

const SESSION_WITH_DATA = { active_artifacts: [{ id: "a1", name: "demo-proposal", type: "proposal" }], note: null };
const TRACE_ONE = { id: "t1", action: "create_spec", result_summary: "spec demo-spec created" };

type UrlHandler = (url: string) => Response;
let handler: UrlHandler;
let fetchMock: ReturnType<typeof vi.fn>;

function isBundleUrl(url: string): boolean {
  return /\/changes\/[^/?]+/.test(url);
}

function changesPage(url: string, changes: ChangeSummary[]) {
  const params = new URLSearchParams(url.includes("?") ? url.slice(url.indexOf("?")) : "");
  const page = Number(params.get("page") || "1");
  const pageSize = Number(params.get("page_size") || "8");
  const start = (page - 1) * pageSize;
  return { items: changes.slice(start, start + pageSize), total: changes.length, page, page_size: pageSize };
}

function makeHandler(changes: ChangeSummary[], session: SessionSummary = { active_artifacts: [], note: null }, traces: unknown[] = []): UrlHandler {
  return (url) => {
    if (isBundleUrl(url)) return jsonResponse(404, { error: { code: "NOT_FOUND", message: "missing" } });
    if (url.includes("/changes")) return jsonResponse(200, changesPage(url, changes));
    if (url.endsWith("/projects/demo")) return jsonResponse(200, { id: "1", name: "Demo", slug: "demo", summary: {}, flows: [] });
    if (url.includes("/session")) return jsonResponse(200, session);
    if (url.includes("/traces")) return jsonResponse(200, traces);
    return jsonResponse(200, []);
  };
}

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("opensddrag.management_token", "t");
  handler = makeHandler(CHANGES);
  fetchMock = vi.fn(async (input: string) => handler(String(input)));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Overview changes-in-progress (REQ-014 delta)", () => {
  it("renders a list row per live change with name, start date and stage", async () => {
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
    const card1 = await screen.findByTestId("change-card-chg-one");
    expect(card1).toBeInTheDocument();
    expect(within(card1).getByTestId("change-stage-chg-one")).toHaveTextContent("Tasks");
    expect(within(card1).getByTestId("change-progress-chg-one")).toHaveTextContent("0/1");
    expect(within(card1).getByText("08 Oct 2026")).toBeInTheDocument();
    expect(within(card1).getByText("Chg one")).toBeInTheDocument();
    expect(screen.queryByTestId("phase-chg-one-Tasks")).not.toBeInTheDocument();
    const card2 = await screen.findByTestId("change-card-chg-two");
    expect(within(card2).getByTestId("change-stage-chg-two")).toHaveTextContent("Propose");
  });

  it("panels: working context + traces remain visible", async () => {
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
    expect(await screen.findByTestId("working-context-panel")).toBeInTheDocument();
    expect(screen.getByTestId("traces-panel")).toBeInTheDocument();
  });
});

describe("OverviewTab two-column layout (overview-grid unit spec)", () => {
  function renderDemo() {
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
  }

  function expectGridColumns(): [HTMLElement, HTMLElement] {
    const grid = document.querySelector(".overview-grid");
    expect(grid).not.toBeNull();
    const columns = grid ? Array.from(grid.children) : [];
    expect(columns, "overview-grid must hold exactly two column divs").toHaveLength(2);
    return [columns[0] as HTMLElement, columns[1] as HTMLElement];
  }

  it("UNIT-1: places the SDD pipeline in the first column and context/trace panels in the second, with a single changes fetch", async () => {
    handler = makeHandler(ONE_CHANGE, SESSION_WITH_DATA, [TRACE_ONE]);
    renderDemo();
    await screen.findByTestId("change-card-chg-one");

    const [left, right] = expectGridColumns();

    expect(within(left).getByText("Live changes")).toBeInTheDocument();
    expect(within(left).getByTestId("change-card-chg-one")).toBeInTheDocument();

    const context = within(right).getByTestId("working-context-panel");
    const traces = within(right).getByTestId("traces-panel");
    expect(context.compareDocumentPosition(traces) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    expect(await within(context).findByText("proposal · demo-proposal")).toBeInTheDocument();
    expect(await within(traces).findByText("create_spec")).toBeInTheDocument();

    const changeCalls = fetchMock.mock.calls.filter((call) => String(call[0]).includes("/changes"));
    expect(changeCalls, "changes must come from props: only the shell fetches /changes once").toHaveLength(1);
  });

  it("UNIT-2: renders exactly one list row for a single-change payload", async () => {
    handler = makeHandler(ONE_CHANGE);
    renderDemo();
    const cards = await screen.findAllByTestId(/^change-card-/);
    expect(cards).toHaveLength(1);
    expect(within(cards[0]).getByTestId("change-stage-chg-one")).toHaveTextContent("Tasks");
    expect(screen.queryAllByTestId(/^phase-chg-one-/)).toHaveLength(0);

    const [left] = expectGridColumns();
    expect(within(left).getByTestId("change-card-chg-one")).toBeInTheDocument();
  });

  it("change cards are links to /p/:slug/c/:change, including lifecycle-less entries", async () => {
    renderDemo();
    const card = await screen.findByTestId("change-card-chg-one");
    expect(card.tagName).toBe("A");
    expect(card).toHaveAttribute("href", "/p/demo/c/chg-one");

    cleanup();
    handler = makeHandler([BARE_CHANGE]);
    renderDemo();
    const bare = await screen.findByTestId("change-card-chg-bare");
    expect(bare.tagName).toBe("A");
    expect(bare).toHaveAttribute("href", "/p/demo/c/chg-bare");
    expect(screen.queryAllByTestId(/^phase-chg-bare-/)).toHaveLength(0);
  });

  it("clicking a change card opens the Change Reader at that URL", async () => {
    handler = (url) => {
      if (isBundleUrl(url)) {
        return jsonResponse(200, {
          change: "chg-one",
          flow: "sdd",
          proposal: {
            id: "p",
            name: "chg-one-proposal",
            type: "proposal",
            status: "draft",
            content: "# P\n\n## Why\nWhy one.",
          },
          design: null,
          specs: [],
          tasks: [],
          task_count: 0,
        });
      }
      return makeHandler(ONE_CHANGE)(url);
    };
    renderDemo();
    fireEvent.click(await screen.findByTestId("change-card-chg-one"));
    expect(await screen.findByTestId("change-reader")).toBeInTheDocument();
    expect(screen.getAllByText("Why one.").length).toBeGreaterThan(0);
  });

  it("paginates the change list and keeps the next page's rows as reader links", async () => {
    const many: ChangeSummary[] = Array.from({ length: 10 }, (_, index) => ({
      change: `chg-${index}`,
      flow: "sdd",
      started_at: "2026-10-01T00:00:00Z",
      updated_at: "2026-10-08T11:00:00Z",
      task_progress: { done: 0, total: 1 },
      phases: [{ name: "Apply", status: "active", desc: "d" }],
    }));
    handler = makeHandler(many);
    renderDemo();
    expect(await screen.findByTestId("change-card-chg-0")).toBeInTheDocument();
    expect(screen.getByTestId("change-card-chg-7")).toBeInTheDocument();
    expect(screen.queryByTestId("change-card-chg-8")).not.toBeInTheDocument();
    expect(screen.getByTestId("changes-pagination")).toHaveTextContent("1 / 2");
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(await screen.findByTestId("change-card-chg-8")).toBeInTheDocument();
    expect(screen.getByTestId("change-card-chg-9")).toHaveAttribute("href", "/p/demo/c/chg-9");
    expect(screen.queryByTestId("change-card-chg-0")).not.toBeInTheDocument();
  });

  it("UNIT-2: renders an entry with empty phases without a phase timeline, keeping the right-column panels", async () => {
    handler = makeHandler([BARE_CHANGE]);
    renderDemo();
    const card = await screen.findByTestId("change-card-chg-bare");
    expect(within(card).getByTestId("change-stage-chg-bare")).toHaveTextContent("—");
    expect(screen.queryAllByTestId(/^phase-chg-bare-/)).toHaveLength(0);

    const [left, right] = expectGridColumns();

    expect(within(left).getByTestId("change-card-chg-bare")).toBeInTheDocument();
    expect(within(right).getByTestId("working-context-panel")).toBeInTheDocument();
    expect(within(right).getByTestId("traces-panel")).toBeInTheDocument();
  });
});
