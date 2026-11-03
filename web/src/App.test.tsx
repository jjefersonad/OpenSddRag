import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "./routes";
import { setToken, setUnauthorizedHandler } from "./api/client";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}
function mockFetch(handler: (url: string) => Response) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => handler(String(url))));
}
function renderAt(path: string) {
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);
}
beforeEach(() => {
  localStorage.clear();
  setUnauthorizedHandler(() => {});
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── REQ-012: AppShell sidebar on authenticated screens ──────────────────────

describe("AppShell (REQ-012)", () => {
  it("sidebar shows logo, docs link, projects list and sign-out + navigates", async () => {
    setToken("t");
    mockFetch((url) => {
      if (url.endsWith("/projects")) return jsonResponse(200, [{ id: "1", name: "Demo", slug: "demo" }]);
      if (url.includes("/projects/demo/changes")) return jsonResponse(200, { items: [], total: 0, page: 1 });
      if (url.endsWith("/projects/demo")) {
        return jsonResponse(200, { id: "1", name: "Demo", slug: "demo", summary: {}, flows: [] });
      }
      return jsonResponse(200, []);
    });
    renderAt("/projects");
    const sidebar = await screen.findByTestId("app-sidebar");
    expect(sidebar).toBeInTheDocument();
    expect(screen.getByText(/docs & design system/i)).toBeInTheDocument();
    const keysLink = within(sidebar).getByRole("link", { name: /api keys/i });
    expect(keysLink).toBeInTheDocument();
    expect(keysLink).toHaveAttribute("href", "/keys");
    expect(keysLink).not.toHaveAttribute("aria-current");
    // Demo appears twice (sidebar link + dashboard card link) — use the
    // sidebar's copy, then assert the detail rendered.
    const sidebarLink = within(sidebar).getByRole("link", { name: "demo" });
    fireEvent.click(sidebarLink);
    expect(await screen.findByRole("heading", { name: "Demo" })).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  it("authenticated /keys renders KeysPage inside the app shell", async () => {
    setToken("t");
    mockFetch((url) => {
      if (url.includes("/keys")) return jsonResponse(200, []);
      if (url.endsWith("/projects")) return jsonResponse(200, []);
      return jsonResponse(200, []);
    });
    renderAt("/keys");
    expect(await screen.findByTestId("app-sidebar")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "API keys" })).toBeInTheDocument();
  });

  it("unauthenticated /keys redirects to login without fetching keys", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderAt("/keys");
    expect(await screen.findByLabelText(/token/i)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("API keys nav item is aria-current on /keys and Projects is not", async () => {
    setToken("t");
    mockFetch((url) => {
      if (url.includes("/keys")) return jsonResponse(200, []);
      if (url.endsWith("/projects")) return jsonResponse(200, []);
      return jsonResponse(200, []);
    });
    renderAt("/keys");
    const sidebar = await screen.findByTestId("app-sidebar");
    const keysLink = within(sidebar).getByRole("link", { name: /api keys/i });
    const projectsLink = within(sidebar).getByRole("link", { name: /projects$/i });
    expect(keysLink).toHaveAttribute("href", "/keys");
    expect(keysLink).toHaveAttribute("aria-current", "page");
    expect(projectsLink).not.toHaveAttribute("aria-current");
  });

  it("sign-out clears the token and returns to the landing", async () => {
    setToken("t");
    setUnauthorizedHandler(() => {});
    mockFetch(() => jsonResponse(200, []));
    renderAt("/projects");
    const signout = await screen.findByRole("button", { name: /sign out/i });
    fireEvent.click(signout);
    expect(await screen.findByTestId("landing-hero")).toBeInTheDocument();
    expect(localStorage.getItem("opensddrag.management_token")).toBeNull();
    // Drain React's post-navigation scheduler ticks inside the live jsdom
    // environment: the DOM scheduler bridges setTimeout; the node scheduler
    // (production react-dom build) bridges setImmediate. Drain a few rounds
    // so cascading ticks have nowhere left to run after teardown.
    for (let round = 0; round < 5; round += 1) {
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
  });
});