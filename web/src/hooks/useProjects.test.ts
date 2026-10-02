import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { useProjects } from "./useProjects";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

const FIXTURES = [
  { id: "1", name: "A", slug: "a" },
  { id: "2", name: "B", slug: "b" },
  { id: "3", name: "C", slug: "c" },
];

beforeEach(() => localStorage.clear());
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── Unit 2: useProjects hook (REQ-004) ──────────────────────────────────────

describe("useProjects", () => {
  it("starts loading and exposes an empty list", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    const { result } = renderHook(() => useProjects());
    expect(result.current.loading).toBe(true);
    expect(result.current.projects).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it("fetches once and exposes the resolved projects", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, FIXTURES));
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useProjects());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.projects).toHaveLength(3);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("sets an error and does not retry on failure", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("network down"));
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useProjects());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeTruthy();
    expect(result.current.projects).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});