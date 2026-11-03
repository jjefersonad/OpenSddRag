import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import TabBar, { type TabBarTab } from "./TabBar";

const TABS: TabBarTab[] = [
  { key: "overview", label: "Overview" },
  { key: "spec", label: "Specs", count: 3 },
  { key: "task", label: "Tasks", count: 8 },
  { key: "hierarchy", label: "Hierarchy" },
];

afterEach(cleanup);

// REQ-020 — tab bar underline style (design D7, task frontend-4 unit-1)
describe("TabBar (REQ-020)", () => {
  it("marks the selected tab: aria-selected, primary colour, 2px accent underline", () => {
    render(<TabBar tabs={TABS} active="spec" onSelect={() => {}} />);
    const specs = screen.getByRole("tab", { name: /Specs 3/i });
    expect(specs.getAttribute("aria-selected")).toBe("true");
    expect(specs.style.color).toBe("var(--color-text-primary)");
    expect(specs.style.borderBottom).toBe("2px solid var(--color-accent)");

    for (const other of TABS.filter((t) => t.key !== "spec")) {
      const el = screen.getByRole("tab", { name: new RegExp(other.label, "i") });
      expect(el.getAttribute("aria-selected")).toBe("false");
      expect(el.style.color).toBe("var(--color-text-secondary)");
      expect(el.style.borderBottom).toBe("2px solid transparent");
    }
  });

  it("renders counts as neutral mono pills, not accent text", () => {
    render(<TabBar tabs={TABS} active="overview" onSelect={() => {}} />);
    const pill = screen.getByRole("tab", { name: /Specs 3/i }).querySelector<HTMLElement>(".tab-count");
    expect(pill).not.toBeNull();
    expect(pill!.textContent).toBe("3");
    expect(pill!.style.fontFamily).toBe("var(--font-mono)");
    expect(pill!.style.color).toBe("var(--color-text-tertiary)");
    expect(pill!.style.background).toBe("rgba(255, 255, 255, 0.06)");
    // not accent-coloured text
    expect(pill!.style.color).not.toBe("var(--color-accent)");
    expect(pill!.style.color).not.toBe("var(--color-accent-hover)");
  });

  it("reports clicks through onSelect", () => {
    const onSelect = vi.fn();
    render(<TabBar tabs={TABS} active="overview" onSelect={onSelect} />);
    screen.getByRole("tab", { name: /Tasks 8/i }).click();
    expect(onSelect).toHaveBeenCalledWith("task");
  });
});