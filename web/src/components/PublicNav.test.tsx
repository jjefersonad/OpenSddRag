import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PublicNav from "./PublicNav";
import tokensCss from "../styles/tokens.css?raw";

afterEach(cleanup);

function renderNav() {
  return render(
    <MemoryRouter>
      <PublicNav />
    </MemoryRouter>,
  );
}

// web-dashboard-ui REQ-018 — public navigation fidelity

describe("PublicNav (REQ-018)", () => {
  it("renders Launch app as a filled accent button and plain links without underline", () => {
    renderNav();
    const launch = screen.getByTestId("nav-launch");
    expect(launch).toHaveTextContent("Launch app →");
    expect(launch).toHaveAttribute("href", "/login");
    // jsdom does not resolve CSS variables: assert the token usage and the
    // token values themselves (#10b981 accent, #04140d on-accent text).
    expect(launch.getAttribute("style")).toContain("var(--color-accent)");
    expect(launch.getAttribute("style")).toContain("var(--color-on-accent)");
    expect(tokensCss).toMatch(/--color-accent:\s*#10b981/);
    expect(tokensCss).toMatch(/--color-on-accent:\s*#04140d/);
    for (const name of ["GitHub", "Docs"]) {
      const link = screen.getByRole("link", { name });
      expect(link).toHaveStyle({ textDecoration: "none" });
      expect(link.getAttribute("style")).not.toContain("--color-accent");
    }
    expect(screen.getByRole("link", { name: "GitHub" })).toHaveAttribute(
      "href",
      "https://github.com/conexaoelite/OpenSddRag",
    );
  });

  it("renders the brand block: glyph square, wordmark and version chip", () => {
    renderNav();
    expect(screen.getByTestId("nav-brand-mark")).toHaveTextContent("⌘");
    expect(screen.getByTestId("nav-brand-mark").getAttribute("style")).toContain("var(--color-accent)");
    expect(screen.getByText("OpenSddRag")).toBeInTheDocument();
    expect(screen.getByTestId("nav-version")).toHaveTextContent(/^v\d+\.\d+\.\d+/);
  });

  it("keeps its content inside a centered 1180px container", () => {
    renderNav();
    expect(screen.getByTestId("nav-inner")).toHaveStyle({ maxWidth: "1180px", margin: "0 auto" });
  });
});
