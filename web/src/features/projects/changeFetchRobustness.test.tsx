import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { routes } from "../../routes";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

type UrlHandler = (url: string) => Response;

const DETAIL = {
  id: "1",
  name: "Demo",
  slug: "demo",
  language: "TypeScript",
  summary: { proposal: 0 },
  flows: [{ flow: "sdd", phase: null, task_progress: { done: 0, total: 0 } }],
  task_progress: { done: 0, total: 0 },
};

let handler: UrlHandler;

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("opensddrag.management_token", "t");
  handler = (url) => {
    if (url.endsWith("/projects/demo")) return jsonResponse(200, DETAIL);
    // Malformed/empty changes payload: NO `items` key.
    if (url.includes("/changes")) return jsonResponse(200, {});
    if (url.includes("/session")) return jsonResponse(200, { active_artifacts: [], note: null });
    if (url.includes("/traces")) return jsonResponse(200, []);
    if (url.endsWith("/flows")) {
      return jsonResponse(200, [{ flow: "sdd", kinds: [{ kind: "proposal", rules: {} }], lifecycle: null }]);
    }
    return jsonResponse(200, []);
  };
  vi.stubGlobal("fetch", vi.fn(async (input: string) => handler(String(input))));
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// dashboard-change-fetch-robustness REQ-001 — a body without `items` must not crash.
it("unit-1: a changes response without items renders the empty state without crashing", async () => {
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/p/demo"] })} />);
  expect(await screen.findByTestId("app-h1")).toBeInTheDocument();
  // Overview resolves to the empty state instead of throwing.
  expect(await screen.findByTestId("changes-empty")).toBeInTheDocument();
});
