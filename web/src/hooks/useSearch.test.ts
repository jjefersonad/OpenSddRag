import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";
import { useSearch } from "./useSearch";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

const RESULTS = [
  { type: "spec", title: "harness-spec", snippet: "s", project: "opensddrag", score: 1, slug: "harness-spec" },
];

beforeEach(() => localStorage.clear());
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── Unit 1: useSearch debounce + abort (web-dashboard-ui REQ-005, design D5) ─

describe("useSearch", () => {
  it("debounces 200ms and aborts the previous in-flight request", async () => {
    vi.useFakeTimers();
    const signals: AbortSignal[] = [];
    const fetchMock = vi.fn((_url: string, init: RequestInit) => {
      signals.push(init.signal as AbortSignal);
      return Promise.resolve(jsonResponse(200, RESULTS));
    });
    vi.stubGlobal("fetch", fetchMock);

    const { result, rerender } = renderHook(({ q }) => useSearch(q), {
      initialProps: { q: "" },
    });

    rerender({ q: "harness" });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/v1/search?q=harness");
    // results mapped with the frontend shape
    expect(result.current.results[0]).toMatchObject({
      type: "spec",
      title: "harness-spec",
      project: "opensddrag",
      score: 1,
    });

    // retype before the next settle → previous controller aborted
    rerender({ q: "harness2" });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(signals[0].aborted).toBe(true);
    expect(signals[1].aborted).toBe(false);
  });
});
