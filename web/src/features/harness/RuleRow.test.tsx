import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import RuleRow from "./RuleRow";
import { setToken } from "../../api/client";
import type { HarnessRule } from "../../api/types";

const RULE: HarnessRule = {
  id: "r1",
  name: "no-console",
  trigger: "on_apply",
  category: "forbidden",
  severity: "error",
  instruction: "no console.log",
  enabled: true,
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

// ── Unit 1: RuleToggle optimistic flow (harness REQ-003) ────────────────────

describe("RuleRow", () => {
  it("flips immediately, PATCHes {enabled:false} with bearer, reverts on failure", async () => {
    let rejectPatch: ((reason?: unknown) => void) | undefined;
    const fetchMock = vi.fn(
      () =>
        new Promise<Response>((_resolve, reject) => {
          rejectPatch = reject;
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<RuleRow slug="demo" rule={RULE} />);
    const toggle = screen.getByRole("checkbox");
    expect(toggle).toBeChecked();

    fireEvent.click(toggle);

    // flips immediately, before the request settles
    expect(toggle).not.toBeChecked();
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(String(url)).toContain("/projects/demo/rules/r1");
    expect(init.method).toBe("PATCH");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer t");
    expect(JSON.parse(String(init.body))).toEqual({ enabled: false });

    rejectPatch?.(new Error("nfail"));
    await waitFor(() => expect(screen.getByRole("checkbox")).toBeChecked());
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
