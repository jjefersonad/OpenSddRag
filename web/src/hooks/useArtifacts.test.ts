import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { useArtifacts } from "./useArtifacts";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

beforeEach(() => localStorage.clear());
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── Unit 2: useArtifacts fetch by type (artifact-management REQ-001) ─────────

describe("useArtifacts", () => {
  it("fetches ?type=<type> once and maps artifacts preserving type/status", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, [
        { id: "1", name: "s1", type: "spec", status: "draft" },
        { id: "2", name: "s2", type: "spec", status: "active" },
      ]),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useArtifacts("demo", "spec"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.artifacts.map((a) => a.type)).toEqual(["spec", "spec"]);
    expect(result.current.artifacts.map((a) => a.status)).toEqual(["draft", "active"]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain("/projects/demo/artifacts?type=spec");
  });

  it("surfaces an error state and keeps the list empty on failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    const { result } = renderHook(() => useArtifacts("demo", "task"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeTruthy();
    expect(result.current.artifacts).toEqual([]);
  });
});
