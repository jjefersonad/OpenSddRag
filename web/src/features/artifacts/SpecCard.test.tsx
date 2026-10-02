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
});
