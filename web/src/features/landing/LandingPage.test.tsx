import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../../routes";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}
beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, [])));
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// REQ-011 — landing page faithful to the prototype

describe("LandingPage (REQ-011)", () => {
  it("renders hero, terminal demo, lifecycle pipeline and memory layers", async () => {
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/"] })} />);
    expect(await screen.findByTestId("landing-hero")).toBeInTheDocument();
    expect(screen.getByText(/persistent memory/i)).toBeInTheDocument();
    expect(screen.getByText(/SDD is built in/i)).toBeInTheDocument();
    expect(screen.getByText(/register[\s\S]*other flows/i)).toBeInTheDocument();
    // terminal demo
    expect(screen.getByTestId("landing-terminal")).toBeInTheDocument();
    expect(screen.getByText(/\/opsr:propose/)).toBeInTheDocument();
    // lifecycle pipeline: 8 phases of the artifact lifecycle
    expect(screen.getByTestId("landing-pipeline")).toBeInTheDocument();
    for (const label of ["Propose", "Spec", "Design", "Tasks", "Apply", "Verify", "Sync", "Archive"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    // three memory layers
    expect(screen.getByTestId("landing-memory-layers")).toBeInTheDocument();
    expect(screen.getAllByText(/Semantic memory/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Episodic memory/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Working context/i).length).toBeGreaterThan(0);
  });

  it("Launch app CTA routes to /login without a token", async () => {
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/"] })} />);
    const cta = await screen.findByTestId("landing-launch");
    fireEvent.click(cta);
    expect(await screen.findByLabelText(/token/i)).toBeInTheDocument();
  });

  it("renders the grid background and glow without hiding the hero (REQ-018)", async () => {
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/"] })} />);
    const grid = await screen.findByTestId("landing-grid-bg");
    const glow = screen.getByTestId("landing-glow");
    for (const layer of [grid, glow]) {
      expect(layer).toHaveStyle({ pointerEvents: "none" });
      expect(layer.style.animationFillMode).not.toBe("both");
    }
    expect(screen.getByTestId("landing-hero")).toBeVisible();
    expect(screen.getByTestId("landing-launch")).toBeVisible();
  });
});
