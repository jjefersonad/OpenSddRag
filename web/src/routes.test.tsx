import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "./routes";
import { setToken } from "./api/client";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

function mockFetch(handler: (url: string) => Response) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => handler(String(url))));
}

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

beforeEach(() => localStorage.clear());
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── Unit 1: routes.tsx (REQ-002/REQ-008) ────────────────────────────────────

describe("routes", () => {
  it("redirects an unknown route to the dashboard", async () => {
    setToken("t");
    mockFetch(() => jsonResponse(200, []));
    renderAt("/xyz");
    expect(await screen.findByText(/new project/i)).toBeInTheDocument();
  });

  it("redirects to /login when no token is stored", async () => {
    mockFetch(() => jsonResponse(200, []));
    renderAt("/");
    expect(await screen.findByLabelText(/token/i)).toBeInTheDocument();
  });

  it("renders the project detail shell at /p/:slug with a token", async () => {
    setToken("t");
    mockFetch((url) =>
      url.endsWith("/projects/demo")
        ? jsonResponse(200, { id: "1", name: "Demo", slug: "demo", summary: { spec: 5 } })
        : jsonResponse(200, []),
    );
    renderAt("/p/demo");
    expect(await screen.findByRole("heading", { name: "Demo" })).toBeInTheDocument();
    expect(screen.getByText(/specs/i)).toBeInTheDocument();
  });
});