import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import TaskRow from "./TaskRow";
import { setToken } from "../../api/client";
import type { Artifact } from "../../api/types";

const TASK: Artifact = {
  id: "t1",
  name: "task-1",
  type: "task",
  status: "active",
  metadata: { done: false },
};

beforeEach(() => {
  localStorage.clear();
  setToken("t");
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── Unit 2: TaskCheckbox optimistic flow (web-dashboard-ui REQ-004) ──────────

describe("TaskRow", () => {
  it("flips done immediately, PATCHes {done:true}, reverts + error on failure", async () => {
    let rejectPatch: ((reason?: unknown) => void) | undefined;
    const fetchMock = vi.fn(
      () =>
        new Promise<Response>((_resolve, reject) => {
          rejectPatch = reject;
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<TaskRow slug="demo" task={TASK} />);
    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).not.toBeChecked();

    fireEvent.click(checkbox);

    expect(checkbox).toBeChecked();
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(String(url)).toContain("/projects/demo/tasks/t1");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(String(init.body))).toEqual({ done: true });

    rejectPatch?.(new Error("nfail"));
    await waitFor(() => expect(screen.getByRole("checkbox")).not.toBeChecked());
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
