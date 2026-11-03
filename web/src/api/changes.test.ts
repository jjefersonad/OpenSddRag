import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getChanges } from "./changes";

let lastUrl = "";

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string) => {
      lastUrl = String(input);
      return {
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0, page: 1, page_size: 8 }),
      } as unknown as Response;
    }),
  );
}

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("opensddrag.management_token", "t");
  stubFetch();
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// dashboard-flows REQ-003 — the All view requests archived history
describe("changes status param (dashboard-flows REQ-003/REQ-004)", () => {
  it("unit-1: status=all requests the All view", async () => {
    await getChanges("demo", 1, 8, "all");
    expect(lastUrl).toContain("status=all");
  });

  it("unit-2: the default request stays live", async () => {
    await getChanges("demo", 1, 8);
    expect(lastUrl).toContain("status=live");
    expect(lastUrl).not.toContain("status=all");
  });
});
