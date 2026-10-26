import { afterEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import ChangeReader from "./ChangeReader";
import { ApiError } from "../../api/client";
import { getChangeBundle } from "../../api/changes";
import type { ChangeBundle } from "../../api/changes";

vi.mock("../../api/changes", () => ({
  getChangeBundle: vi.fn(),
  getChanges: vi.fn(),
}));

const getChangeBundleMock = getChangeBundle as unknown as Mock;

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

const BUNDLE: ChangeBundle = {
  change: "web-change-reader",
  flow: "sdd",
  proposal: {
    id: "p1",
    name: "web-change-reader-proposal",
    type: "proposal",
    status: "draft",
    content: "# web-change-reader\n\n## Why\nA human cannot read what a change did\n\n## What Changes\n- Add a reader.",
  },
  design: {
    id: "d1",
    name: "web-change-reader-design",
    type: "design",
    status: "draft",
    content: "# Design\n\n## Context\nREST bundle, not MCP.\n\n## Decisions\n\n### Decision: D1 REST\n**Chosen:** management API.",
  },
  specs: [
    {
      id: "s1",
      name: "web-change-reader-change-reader-spec",
      type: "spec",
      status: "draft",
      content: "# Spec A\n\n## Purpose\nRead one change.\n\n### Requirement: REQ-001 Titles\nThe UI SHALL show Why.",
    },
    {
      id: "s2",
      name: "web-change-reader-web-api-management-spec",
      type: "spec",
      status: "draft",
      content: "# Spec B\n\n## Purpose\nOne HTTP read.\n\n### Requirement: REQ-014 Bundle\nThe API SHALL return content.",
    },
  ],
  tasks: [
    { name: "t-fonts", status: "archived", content: "## Goal\nLoad IBM Plex fonts", done: true },
    { name: "t-2", status: "archived", content: "## Goal\nGoal two", done: true },
    { name: "t-3", status: "archived", content: "## Goal\nGoal three", done: true },
    { name: "t-4", status: "draft", content: "## Goal\nGoal four pending", done: false },
  ],
  task_count: 4,
};

describe("ChangeReader (REQ-002 / REQ-003 / REQ-021)", () => {
  it("renders proposal, specs, design and tasks in order with bodies, excluding other changes", async () => {
    getChangeBundleMock.mockResolvedValue(BUNDLE);
    render(<ChangeReader slug="demo" change="web-change-reader" />);
    const reader = await screen.findByTestId("change-reader");
    expect(reader.textContent).toContain("A human cannot read what a change did");
    expect(reader.textContent).toContain("Read one change.");
    expect(reader.textContent).toContain("One HTTP read.");
    expect(reader.textContent).toContain("REST bundle, not MCP.");
    expect(reader.textContent).toContain("Load IBM Plex fonts");
    expect(reader.textContent).not.toContain("web-ui-prototype-fidelity");
    expect(within(reader).getByTestId("change-briefing")).toHaveTextContent("Web change reader");
    expect(within(reader).getByTestId("reader-task-progress")).toHaveTextContent("3/4 done");

    const labels = within(reader).getAllByText(/^(Proposal|Specs|Design|Tasks)$/);
    expect(labels.map((el) => el.textContent)).toEqual(["Proposal", "Specs", "Design", "Tasks"]);
  });

  it("limits the body to the kinds of the selected stage", async () => {
    getChangeBundleMock.mockResolvedValue(BUNDLE);
    const { rerender } = render(<ChangeReader slug="demo" change="web-change-reader" stageKinds={["proposal"]} />);
    expect((await screen.findAllByText("A human cannot read what a change did")).length).toBeGreaterThan(0);
    expect(screen.queryAllByText("Read one change.")).toHaveLength(0);
    expect(screen.queryAllByText("REST bundle, not MCP.")).toHaveLength(0);
    expect(screen.queryAllByText("Load IBM Plex fonts")).toHaveLength(0);

    rerender(<ChangeReader slug="demo" change="web-change-reader" stageKinds={["task"]} />);
    expect(screen.getAllByText("Load IBM Plex fonts").length).toBeGreaterThan(0);
    expect(screen.queryAllByText("A human cannot read what a change did")).toHaveLength(0);

    rerender(<ChangeReader slug="demo" change="web-change-reader" stageKinds={[]} />);
    expect(screen.getByTestId("stage-empty")).toHaveTextContent("Nothing in this stage yet.");
    expect(screen.queryByText("Load IBM Plex fonts")).not.toBeInTheDocument();
  });

  it("shows 'No design yet' when design is null and still renders other sections", async () => {
    getChangeBundleMock.mockResolvedValue({ ...BUNDLE, design: null });
    render(<ChangeReader slug="demo" change="web-change-reader" />);
    expect(await screen.findByText("No design yet")).toBeInTheDocument();
    expect(screen.getAllByText("A human cannot read what a change did").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Load IBM Plex fonts").length).toBeGreaterThan(0);
  });

  it("marks archived tasks done, shows Goal on draft tasks, and surfaces a 404", async () => {
    getChangeBundleMock.mockResolvedValue(BUNDLE);
    const { unmount } = render(<ChangeReader slug="demo" change="web-change-reader" />);
    const archived = await screen.findByRole("checkbox", { name: /toggle t-fonts/i });
    expect(archived).toBeChecked();
    expect(screen.getAllByText("Load IBM Plex fonts").length).toBeGreaterThan(0);
    const draft = screen.getByRole("checkbox", { name: /toggle t-4/i });
    expect(draft).not.toBeChecked();
    expect(screen.getAllByText("Goal four pending").length).toBeGreaterThan(0);
    unmount();

    getChangeBundleMock.mockRejectedValue(new ApiError("NOT_FOUND", "missing"));
    render(<ChangeReader slug="demo" change="does-not-exist" />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/change not found/i);
    expect(screen.queryByTestId("change-reader")).not.toBeInTheDocument();
    expect(screen.queryByText("A human cannot read what a change did")).not.toBeInTheDocument();
  });
});
