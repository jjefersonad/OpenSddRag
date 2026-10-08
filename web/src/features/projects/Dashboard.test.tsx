import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "./Dashboard";
import type { Project } from "../../api/types";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

function mockDashboardFetch(projects: Project[]) {
  vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, projects)));
}

beforeEach(() => localStorage.clear());
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// REQ-013 — rich dashboard cards (stage, language, relative time, progress)

const richProject: Project & {
  language?: string;
  phase?: string | null;
  task_progress?: { done: number; total: number };
} = {
  id: "1",
  name: "Demo Proj",
  slug: "demo-proj",
  description: "A demo capability",
  language: "Python",
  phase: "Design",
  task_progress: { done: 3, total: 8 },
  updated_at: new Date(Date.now() - 3 * 3600 * 1000).toISOString(),
};

const noLifecycleProject: Project & { phase?: string | null; task_progress?: { done: number; total: number } } = {
  id: "2",
  name: "Bare Proj",
  slug: "bare-proj",
  description: null,
  language: "",
  phase: null,
  task_progress: { done: 0, total: 2 },
};

describe("Dashboard cards (REQ-013)", () => {
  it("renders stage chip, description, language, relative time and progress", async () => {
    mockDashboardFetch([richProject]);
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    const card = await screen.findByTestId("project-card-demo-proj");
    expect(card).toBeInTheDocument();
    expect(screen.getByText("Design")).toBeInTheDocument(); // stage chip
    expect(screen.getByText("A demo capability")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText(/3 \/ 8 tasks/i)).toBeInTheDocument();
    expect(screen.getByText(/3h ago|3 hours ago/i)).toBeInTheDocument();
  });

  it("omits the stage chip when the flow declares no lifecycle", async () => {
    mockDashboardFetch([noLifecycleProject]);
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    await screen.findByTestId("project-card-bare-proj");
    expect(screen.queryByText("None")).not.toBeInTheDocument();
    expect(screen.queryByTestId("stage-chip-bare-proj")).not.toBeInTheDocument();
    expect(screen.getByText(/0 \/ 2 tasks/i)).toBeInTheDocument();
  });

  it("renders the empty state for an empty registry", async () => {
    mockDashboardFetch([]);
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("dashboard-empty")).toBeInTheDocument();
  });
});
