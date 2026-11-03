import { afterEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import ArtifactsTab from "./ArtifactsTab";
import type { Artifact } from "../../api/types";
import { getArtifact, listArtifacts } from "../../api/artifacts";

vi.mock("../../api/artifacts", () => ({
  listArtifacts: vi.fn(),
  getArtifact: vi.fn(),
}));

const listArtifactsMock = listArtifacts as unknown as Mock;
const getArtifactMock = getArtifact as unknown as Mock;

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

// Real listing shape (web-api REQ-019): summary rows carry id, name, type,
// status, flow, updated_at — no `content`. Content arrives only when the
// fetcher opts in with include=content.
const BASE_SUMMARY: Artifact = {
  id: "s1",
  name: "alpha-spec",
  type: "spec",
  status: "draft",
  flow: "sdd",
  updated_at: "2026-10-22T10:00:00Z",
};

const SPEC_CONTENT_WITH_TWO_REQS = [
  "# Session Spec",
  "",
  "## Requirements",
  "",
  "### Requirement: REQ-001 Token expiry",
  "The auth service SHALL issue tokens that expire after 15 minutes.",
  "",
  "### Requirement: REQ-002 Refresh rotation",
  "The client SHALL rotate refresh tokens on every use.",
  "",
  "#### Scenario: refresh reuse",
  "- **WHEN** a used refresh token is presented",
  "- **THEN** the session is revoked",
].join("\n");

const DEFAULT_LIST: Artifact[] = [BASE_SUMMARY];
const WITH_CONTENT_LIST: Artifact[] = [
  { ...BASE_SUMMARY, content: SPEC_CONTENT_WITH_TWO_REQS },
];

describe("ArtifactsTab specs fetching (REQ-015 + web-api include=content)", () => {
  it("uses real-API payload shapes: summaries without content, include run with content", () => {
    expect(DEFAULT_LIST[0]).not.toHaveProperty("content");
    expect(WITH_CONTENT_LIST[0]).toHaveProperty("content", expect.any(String));
    expect(DEFAULT_LIST[0]).toMatchObject({
      id: "s1",
      name: "alpha-spec",
      type: "spec",
      status: "draft",
      flow: "sdd",
      updated_at: expect.any(String),
    });
  });

  // Unit spec: WHEN the Specs tab mounts THEN listArtifacts is called with
  // type=spec and include=content exactly once and no getArtifact calls are
  // made; the mock payload for the default list has no content field (real
  // API shape) while the include=content mock has it.
  it("fetches specs once with include=content, never calls getArtifact, and renders counts from content", async () => {
    listArtifactsMock.mockImplementation((...args: unknown[]) =>
      Promise.resolve(args.includes(true) ? WITH_CONTENT_LIST : DEFAULT_LIST),
    );

    render(<ArtifactsTab slug="demo" type="spec" />);

    expect(await screen.findByText("2 requirements")).toBeInTheDocument();
    expect(listArtifactsMock).toHaveBeenCalledTimes(1);
    const args = listArtifactsMock.mock.calls[0];
    expect(args[0]).toBe("demo");
    expect(args).toContain("spec"); // type=spec filter requested
    expect(args).toContain(true); // include=content opt-in requested
    expect(getArtifactMock).not.toHaveBeenCalled();
    // Cards are collapsed by default (REQ-015) — expand to prove the content
    // arrived inside the single list request (no per-artifact fetch).
    fireEvent.click(screen.getByRole("button", { name: /alpha-spec/i }));
    expect(await screen.findByText(/SHALL issue tokens that expire after 15 minutes/i)).toBeInTheDocument();
    expect(screen.queryByText(/No parsed requirements/i)).not.toBeInTheDocument();
  });

  it("fetches proposal and design with include=content and renders the body (or raw fallback)", async () => {
    const proposal = {
      ...BASE_SUMMARY,
      id: "p1",
      name: "alpha-proposal",
      type: "proposal",
      content: "# P\n\n## Why\nThe problem is readable now.",
    };
    const design = {
      ...BASE_SUMMARY,
      id: "d1",
      name: "alpha-design",
      type: "design",
      content: "# Design\n\n## Context\nDecisions live here.\n\nUnstructured leftover body.",
    };
    listArtifactsMock.mockImplementation((...args: unknown[]) => {
      if (!args.includes(true)) return Promise.resolve([BASE_SUMMARY]);
      if (args.includes("proposal")) return Promise.resolve([proposal]);
      if (args.includes("design")) return Promise.resolve([design]);
      return Promise.resolve([]);
    });

    const { unmount } = render(<ArtifactsTab slug="demo" type="proposal" />);
    expect(await screen.findByText(/The problem is readable now/i)).toBeInTheDocument();
    expect(listArtifactsMock.mock.calls[0]).toContain(true);
    expect(screen.queryByText(/None recorded/i)).not.toBeInTheDocument();
    unmount();

    render(<ArtifactsTab slug="demo" type="design" />);
    expect(await screen.findByText(/Decisions live here/i)).toBeInTheDocument();
    expect(screen.getByText(/Unstructured leftover body/i)).toBeInTheDocument();
    expect(screen.queryByText(/None recorded/i)).not.toBeInTheDocument();
    const designCall = listArtifactsMock.mock.calls.find((call) => call.includes("design"));
    expect(designCall).toContain(true);
  });
});