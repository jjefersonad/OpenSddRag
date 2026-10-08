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

// ── REQ-002: routing model with public landing ─────────────────────────────

describe("routes (web-ui-design-alignment REQ-002)", () => {
  it("renders the public landing at / with no token (no redirect)", async () => {
    mockFetch(() => jsonResponse(200, []));
    renderAt("/");
    expect(await screen.findByTestId("landing-hero")).toBeInTheDocument();
  });

  it("redirects /projects to /login when no token is stored", async () => {
    mockFetch(() => jsonResponse(200, []));
    renderAt("/projects");
    expect(await screen.findByLabelText(/token/i)).toBeInTheDocument();
  });

  it("redirects /p/:slug to /login when no token is stored", async () => {
    mockFetch(() => jsonResponse(200, []));
    renderAt("/p/demo");
    expect(await screen.findByLabelText(/token/i)).toBeInTheDocument();
  });

  it("renders the dashboard at /projects with a token", async () => {
    setToken("t");
    mockFetch(() => jsonResponse(200, []));
    renderAt("/projects");
    expect(await screen.findByText(/new project/i)).toBeInTheDocument();
  });

  it("renders the project detail shell at /p/:slug with a token", async () => {
    setToken("t");
    mockFetch((url) => {
      if (url.endsWith("/projects/demo")) {
        return jsonResponse(200, {
          id: "1",
          name: "Demo",
          slug: "demo",
          summary: { spec: 5 },
          flows: [{ flow: "sdd", phase: null, task_progress: { done: 0, total: 0 } }],
        });
      }
      if (url.endsWith("/flows")) {
        return jsonResponse(200, [
          { flow: "sdd", kinds: [{ kind: "spec", rules: {} }], lifecycle: null },
        ]);
      }
      return jsonResponse(200, []);
    });
    renderAt("/p/demo");
    expect(await screen.findByRole("heading", { name: "Demo" })).toBeInTheDocument();
    expect(screen.getByText(/specs/i)).toBeInTheDocument();
  });

  it("redirects an unknown route to /", async () => {
    setToken("t");
    mockFetch(() => jsonResponse(200, []));
    renderAt("/xyz");
    expect(await screen.findByTestId("landing-hero")).toBeInTheDocument();
  });
});
