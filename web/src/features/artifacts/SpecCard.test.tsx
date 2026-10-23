import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import SpecCard from "./SpecCard";
import type { Artifact } from "../../api/types";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const specA: Artifact = {
  id: "1",
  name: "auth-spec",
  type: "spec",
  status: "draft",
  content: "# Auth\n\n#### Scenario: login\n- **WHEN** valid creds\n- **THEN** ok",
};
const specB: Artifact = {
  id: "2",
  name: "billing-spec",
  type: "spec",
  status: "active",
  content: "# Billing\n\n#### Scenario: charge\n- **WHEN** card ok\n- **THEN** charged",
};

// REQ-015 (design D5/D6): a spec whose content carries two `### Requirement:`
// blocks. REQ-001 is SHALL-only, REQ-002 adds a WHEN/THEN scenario pair —
// together they cover both requirement body shapes.
const specTwoRequirements: Artifact = {
  id: "10",
  name: "session-spec",
  type: "spec",
  status: "draft",
  content: [
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
  ].join("\n"),
};

// ── Unit 1: SpecCard expand/collapse (AGENT_GUIDE §5; artifact-management REQ-002) ──

describe("SpecCard", () => {
  it("toggles scenarios visibility via an aria-expanded header", () => {
    render(<SpecCard artifact={specA} />);

    const header = screen.getByRole("button", { name: /auth-spec/i });
    expect(header).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText(/valid creds/)).not.toBeInTheDocument();

    fireEvent.click(header);
    expect(header).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/valid creds/)).toBeInTheDocument();

    fireEvent.click(header);
    expect(header).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText(/valid creds/)).not.toBeInTheDocument();
  });

  it("keeps state independent across cards", () => {
    render(
      <div>
        <SpecCard artifact={specA} />
        <SpecCard artifact={specB} />
      </div>,
    );

    fireEvent.click(screen.getByRole("button", { name: /auth-spec/i }));

    expect(screen.getByRole("button", { name: /auth-spec/i })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByRole("button", { name: /billing-spec/i })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(screen.getByText(/valid creds/)).toBeInTheDocument();
    expect(screen.queryByText(/card ok/)).not.toBeInTheDocument();
  });

  // ── Unit 1: requirement-count header + structured body (REQ-015, D5/D6) ──
  // Unit spec: WHEN given a spec with 2 requirements THEN it renders collapsed
  // with the name, `2 requirements` and the status chip; WHEN clicked THEN
  // each requirement shows its SHALL text and WHEN/THEN scenarios (WHEN in
  // amber).

  it("shows the requirement count on the collapsed header and the structured body when expanded", () => {
    render(<SpecCard artifact={specTwoRequirements} />);

    const header = screen.getByRole("button", { name: /session-spec/i });
    expect(header).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("2 requirements")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
    expect(screen.queryByText(/SHALL issue tokens/)).not.toBeInTheDocument();

    fireEvent.click(header);
    expect(header).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("REQ-001")).toBeInTheDocument();
    expect(screen.getByText("Token expiry")).toBeInTheDocument();
    expect(
      screen.getByText(/SHALL issue tokens that expire after 15 minutes/i),
    ).toBeInTheDocument();
    expect(screen.getByText("REQ-002")).toBeInTheDocument();
    expect(screen.getByText("Refresh rotation")).toBeInTheDocument();
    expect(
      screen.getByText(/SHALL rotate refresh tokens on every use/i),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /refresh reuse/i }));
    const when = screen.getByTestId("scenario-when");
    expect(when.textContent).toContain("WHEN a used refresh token is presented");
    expect(when.style.color).toBe("var(--color-warn)");
    const then = screen.getByTestId("scenario-then");
    expect(then.textContent).toContain("THEN the session is revoked");
    expect(then.style.color).toBe("var(--color-text-primary)");
  });

  // ── Unit 2: raw-content fallback (REQ-015, D6) ──
  // Unit spec: WHEN the spec content has no `### Requirement:` blocks THEN the
  // expanded card renders the raw content and the text "No parsed
  // requirements" never appears.

  it("renders raw content when there are no requirement blocks and never shows the parsed-fallback text", () => {
    const noReqSpec: Artifact = {
      id: "11",
      name: "notes-spec",
      type: "spec",
      status: "draft",
      content: "# Notes\n\nFree-form notes without requirement blocks.",
    };

    render(<SpecCard artifact={noReqSpec} />);
    const header = screen.getByRole("button", { name: /notes-spec/i });
    fireEvent.click(header);

    expect(
      screen.getByText(/Free-form notes without requirement blocks/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/No parsed requirements/i)).not.toBeInTheDocument();
  });
});
