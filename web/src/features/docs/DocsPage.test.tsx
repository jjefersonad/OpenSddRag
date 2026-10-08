import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../../routes";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

beforeEach(() => {
  localStorage.clear(); // logged out — docs must be public
  vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, [])));
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// REQ-009 — docs page with sticky TOC of the agent-guide sections

const SECTIONS = [
  "Overview",
  "Quickstart",
  "SDD workflow",
  "Artifact formats",
  "Harness rules",
  "Agent operating rules",
  "Principles",
  "Color",
  "Typography",
  "Components",
];

describe("DocsPage (REQ-009)", () => {
  it("renders the sticky TOC with the guide sections and PublicNav", async () => {
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/docs"] })} />);
    const toc = await screen.findByTestId("docs-toc");
    expect(toc).toBeInTheDocument();
    for (const section of SECTIONS) {
      expect(screen.getAllByText(section).length).toBeGreaterThan(0);
    }
    // public chrome while logged out
    expect(screen.getByTestId("public-nav")).toBeInTheDocument();
    // section bodies render
    expect(screen.getByTestId("docs-section-color")).toBeInTheDocument();
    expect(screen.getByTestId("docs-section-typography")).toBeInTheDocument();
    expect(screen.getByTestId("docs-section-components")).toBeInTheDocument();
  });
});