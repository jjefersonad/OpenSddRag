import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../../routes";
import type { ChangeSummary } from "../../api/changes";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}
type UrlHandler = (url: string) => Response;
let handler: UrlHandler;

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

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("opensddrag.management_token", "t");
  handler = (url) => {
    if (url.includes("/changes")) return jsonResponse(200, CHANGES);
    if (url.endsWith("/projects/demo")) return jsonResponse(200, { id: "1", name: "Demo", slug: "demo", summary: {}, flows: [] });
    if (url.includes("/session")) return jsonResponse(200, { active_artifacts: [], note: null });
    if (url.includes("/traces")) return jsonResponse(200, []);
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

describe("Overview changes-in-progress (REQ-014 delta)", () => {
  it("renders a card per live change with its vertical timeline", async () => {
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
    const card1 = await screen.findByTestId("change-card-chg-one");
    expect(card1).toBeInTheDocument();
    expect(await within(card1).findByTestId("phase-chg-one-Tasks")).toBeInTheDocument();
    expect(within(card1).getByText("Propose")).toBeInTheDocument();
    const card2 = await screen.findByTestId("change-card-chg-two");
    expect(within(card2).getByText("Propose")).toBeInTheDocument();
  });

  it("panels: working context + traces remain visible", async () => {
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
    expect(await screen.findByTestId("working-context-panel")).toBeInTheDocument();
    expect(screen.getByTestId("traces-panel")).toBeInTheDocument();
  });
});
