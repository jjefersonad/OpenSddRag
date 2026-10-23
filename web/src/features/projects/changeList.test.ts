import { describe, expect, it } from "vitest";
import type { ChangeSummary } from "../../api/changes";
import { changeStage, formatChangeDate, paginateChanges } from "./changeList";

const base: ChangeSummary = {
  change: "chg-one",
  flow: "sdd",
  updated_at: "2026-10-08T11:00:00Z",
  task_progress: { done: 0, total: 1 },
  phases: [],
};

describe("change list helpers", () => {
  it("uses the active phase as the stage, then the last phase, then an em dash", () => {
    expect(
      changeStage({
        ...base,
        phases: [
          { name: "Propose", status: "done", desc: "" },
          { name: "Tasks", status: "active", desc: "" },
        ],
      }),
    ).toBe("Tasks");
    expect(
      changeStage({
        ...base,
        phases: [
          { name: "Propose", status: "done", desc: "" },
          { name: "Archive", status: "done", desc: "" },
        ],
      }),
    ).toBe("Archive");
    expect(changeStage(base)).toBe("—");
  });

  it("formats a UTC timestamp as a compact start date", () => {
    expect(formatChangeDate("2026-10-08T11:00:00Z")).toBe("08 Oct 2026");
    expect(formatChangeDate(null)).toBe("—");
  });

  it("paginates a list into fixed-size pages", () => {
    const items = Array.from({ length: 10 }, (_, i) => i);
    expect(paginateChanges(items, 0, 8)).toEqual([0, 1, 2, 3, 4, 5, 6, 7]);
    expect(paginateChanges(items, 1, 8)).toEqual([8, 9]);
  });
});
