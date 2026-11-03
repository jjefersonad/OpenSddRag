import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  apiRequest,
  getToken,
  optimistic,
  setToken,
  setUnauthorizedHandler,
} from "./client";

/** Portable fake of the subset of `Response` the client consumes. */
function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response;
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── Unit 1: apiClient.request (REQ-003/REQ-004) ──────────────────────────────

describe("apiRequest", () => {
  it("injects Authorization: Bearer <token> and returns parsed JSON", async () => {
    setToken("abc");
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const data = await apiRequest("/projects");

    expect(data).toEqual({ ok: true });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer abc");
  });

  it("omits Authorization when no token is stored", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, {}));
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/projects");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it("on 401 clears the token and invokes the unauthorized handler", async () => {
    setToken("abc");
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(401, { error: { code: "UNAUTHORIZED", message: "nope" } }),
      ),
    );

    await expect(apiRequest("/projects")).rejects.toBeInstanceOf(ApiError);
    expect(getToken()).toBeNull();
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("normalizes 4xx/5xx errors into ApiError {code,message,details}", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(409, {
          error: { code: "CONFLICT", message: "dup", details: ["slug"] },
        }),
      ),
    );

    await expect(apiRequest("/projects")).rejects.toMatchObject({
      code: "CONFLICT",
      message: "dup",
      details: ["slug"],
    });
  });
});

// ── Unit 3: optimistic() helper (REQ-004, design D8) ────────────────────────

describe("optimistic", () => {
  it("applies the local mutation first and keeps it on success", async () => {
    const state = [1, 2, 3];
    const result = await optimistic({
      apply: () => state.push(4),
      action: async () => "ok",
      rollback: () => state.pop(),
    });
    expect(result).toBe("ok");
    expect(state).toEqual([1, 2, 3, 4]);
  });

  it("rolls back and surfaces the error on failure", async () => {
    const state = [{ done: false }];
    await expect(
      optimistic({
        apply: () => {
          state[0].done = true;
        },
        action: async () => {
          throw new Error("boom");
        },
        rollback: () => {
          state[0].done = false;
        },
      }),
    ).rejects.toThrow("boom");
    expect(state[0].done).toBe(false);
  });
});