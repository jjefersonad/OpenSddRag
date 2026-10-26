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
    expect(screen.getByText(/3\/8 tasks/i)).toBeInTheDocument();
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
    expect(screen.getByText(/0\/2 tasks/i)).toBeInTheDocument();
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

// REQ-013 — prototype-faithful grid, header and card (web-ui-prototype-fidelity)

const PHASE_NAMES = ["Propose", "Spec", "Design", "Tasks", "Apply", "Verify", "Sync", "Archive"];

function phasesAt(activeIndex: number) {
  return PHASE_NAMES.map((name, i) => ({
    name,
    status: i < activeIndex ? "done" : i === activeIndex ? "active" : "pending",
  })) as NonNullable<Project["phases"]>;
}

const pipelineProject: Project = {
  id: "9",
  name: "Payments Service",
  slug: "payments-service",
  description: "Stripe-backed billing & subscription engine.",
  language: "TypeScript",
  phase: "Tasks",
  phases: phasesAt(3),
  task_progress: { done: 4, total: 8 },
  updated_at: new Date(Date.now() - 12 * 60_000).toISOString(),
};

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe("Dashboard prototype fidelity (REQ-013)", () => {
  it("renders name, slug, stage chip, pipeline bars and 4/8 tasks", async () => {
    mockDashboardFetch([pipelineProject]);
    renderDashboard();
    const card = await screen.findByTestId("project-card-payments-service");
    expect(card).toHaveTextContent("Payments Service");
    expect(card).toHaveTextContent("payments-service");
    expect(screen.getByTestId("stage-chip-payments-service")).toHaveTextContent("Tasks");
    const bars = screen.getByTestId("pipeline-payments-service").children;
    expect(bars).toHaveLength(8);
    expect(Array.from(bars).map((b) => b.getAttribute("data-state"))).toEqual([
      "done", "done", "done", "active", "pending", "pending", "pending", "pending",
    ]);
    expect(screen.getByTestId("task-progress-payments-service")).toHaveTextContent("4/8 tasks");
  });

  it("renders the header subtitle, the grid class and the New project button", async () => {
    const four = ["a", "b", "c", "d"].map((slug, i) => ({ id: String(i), name: slug, slug }) as Project);
    mockDashboardFetch(four);
    renderDashboard();
    expect(await screen.findByText("4 registered · multi-tenant artifact memory")).toBeInTheDocument();
    expect(screen.getByRole("list")).toHaveClass("dashboard-grid");
    expect(screen.getByRole("button", { name: "+ New project" })).toBeInTheDocument();
  });

  it("omits chip and pipeline when the project has no stage, without error", async () => {
    mockDashboardFetch([{ ...noLifecycleProject, phases: [] }]);
    renderDashboard();
    await screen.findByTestId("project-card-bare-proj");
    expect(screen.queryByTestId("stage-chip-bare-proj")).not.toBeInTheDocument();
    expect(screen.queryByTestId("pipeline-bare-proj")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("tolerates an older API payload without phase/phases/task_progress", async () => {
    mockDashboardFetch([{ id: "7", name: "Legacy", slug: "legacy", language: "Go" } as Project]);
    renderDashboard();
    const card = await screen.findByTestId("project-card-legacy");
    expect(card).toHaveTextContent("Legacy");
    expect(card).toHaveTextContent("legacy");
    expect(card).toHaveTextContent("Go");
    expect(screen.getByTestId("task-progress-legacy")).toHaveTextContent("0/0 tasks");
  });

  it("shows the success notice carried from a project deletion", async () => {
    mockDashboardFetch([]);
    render(
      <MemoryRouter initialEntries={[{ pathname: "/projects", state: { notice: "Project CRUD Check was deleted." } }]}>
        <Dashboard />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Project CRUD Check was deleted.");
  });
});
