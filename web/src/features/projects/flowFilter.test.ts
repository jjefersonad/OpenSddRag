import { describe, expect, it } from "vitest";

import { buildTabs, flowOptions } from "./ProjectDetail";

const FLOWS = [
  { flow: "sdd", kinds: [{ kind: "proposal" }, { kind: "spec" }, { kind: "task" }], lifecycle: [] },
  { flow: "websec", kinds: [{ kind: "finding" }, { kind: "poc" }], lifecycle: [] },
] as never;

// dashboard-flows REQ-001 — registry-driven flow axis
describe("flow axis (dashboard-flows REQ-001)", () => {
  it("unit-1: offers every registry flow, including one with no artifacts", () => {
    const opts = flowOptions(FLOWS);
    expect(opts.map((o) => o.value)).toEqual([null, "sdd", "websec"]);
    // a kind of a flow the project has no artifacts for is still surfaced
    const tabs = buildTabs(null, FLOWS, null);
    expect(tabs.some((t) => t.key === "finding")).toBe(true);
  });
});

// dashboard-flows REQ-002 — flow-filtered artifacts
describe("flow filtering (dashboard-flows REQ-002)", () => {
  it("unit-2: selecting a flow tags the tabs with that flow; none lists all", () => {
    const all = buildTabs(null, FLOWS, null);
    expect(all.find((t) => t.key === "finding")?.flow).toBeUndefined();

    const ws = buildTabs(null, FLOWS, "websec");
    const kindTabs = ws.filter((t) => t.type);
    expect(kindTabs.length).toBeGreaterThan(0);
    for (const t of kindTabs) expect(t.flow).toBe("websec");
    // only the selected flow's kinds are shown
    expect(ws.some((t) => t.key === "proposal")).toBe(false);
    expect(ws.some((t) => t.key === "finding")).toBe(true);
  });
});
