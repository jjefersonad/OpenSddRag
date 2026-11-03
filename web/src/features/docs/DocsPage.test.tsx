import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../../routes";
import { DESIGN_TOKENS, type DesignToken } from "./designTokens";
import { TOC_SECTIONS } from "./docsToc";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

beforeEach(() => {
  localStorage.clear(); // logged out — docs must be public
  vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, [])));
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// REQ-009 — docs page with sticky TOC of the agent-guide sections

const SECTIONS = [...TOC_SECTIONS];

describe("DocsPage (REQ-009)", () => {
  it("renders the sticky TOC with the guide sections and PublicNav", async () => {
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/docs"] })} />);
    const toc = await screen.findByTestId("docs-toc");
    expect(toc).toBeInTheDocument();
    for (const section of SECTIONS) {
      expect(screen.getAllByText(section).length).toBeGreaterThan(0);
    }
    // public chrome while logged out
    expect(screen.getByTestId("public-nav")).toBeInTheDocument();
    // section bodies render
    expect(screen.getByTestId("docs-section-color")).toBeInTheDocument();
    expect(screen.getByTestId("docs-section-typography")).toBeInTheDocument();
    expect(screen.getByTestId("docs-section-components")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Docs design-system reference (design D10 / REQ-009): DocsPage renders live
// swatches, type samples and component samples driven by designTokens.ts, whose
// values must stay in sync with src/styles/tokens.css.
// ---------------------------------------------------------------------------

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

async function renderDocs() {
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/docs"] })} />);
  return screen.findByTestId("docs-toc");
}

describe("DocsPage design-system samples (D10 / REQ-009)", () => {
  // jsdom cannot resolve CSS var() values, so colour fidelity is asserted via
  // a data-hex attribute (or inline style) instead of a computed background.
  it("renders one color swatch (square + name + hex) per design token in the Color section", async () => {
    const tokens: DesignToken[] = DESIGN_TOKENS;
    await renderDocs();
    const colorSection = screen.getByTestId("docs-section-color");
    for (const token of tokens) {
      const swatch = within(colorSection).getByTestId(`docs-swatch-${slugify(token.name)}`);
      // swatch shows the token name and its hex value as visible text
      const text = (swatch.textContent ?? "").toLowerCase().replace(/[^a-z0-9#]+/g, "");
      expect(text, `swatch for ${token.name} must show the token name`).toContain(
        token.name.toLowerCase().replace(/[^a-z0-9]+/g, ""),
      );
      expect(text, `swatch for ${token.name} must show the hex value`).toContain(
        token.hex.toLowerCase().replace(/[^a-z0-9#]+/g, ""),
      );
      // the colour square carries the exact token value
      const square = swatch.querySelector<HTMLElement>("[data-hex]");
      expect(square, `swatch ${token.name} must contain a colour square with data-hex`).not.toBeNull();
      expect((square as HTMLElement).dataset.hex?.replace(/\s+/g, "").toLowerCase()).toBe(
        token.hex.replace(/\s+/g, "").toLowerCase(),
      );
    }
    // no extra or missing swatches — exactly one per declared token
    const swatchCount = colorSection.querySelectorAll("[data-testid^='docs-swatch-']").length;
    expect(swatchCount).toBe(tokens.length);
  });

  it("shows type samples in IBM Plex Sans and IBM Plex Mono and lists every TOC section", async () => {
    await renderDocs();
    const toc = screen.getByTestId("docs-toc");
    expect(toc.querySelectorAll("a")).toHaveLength(SECTIONS.length);
    for (const section of SECTIONS) {
      expect(within(toc).getAllByText(section).length).toBeGreaterThan(0);
    }
    const typeSection = screen.getByTestId("docs-section-typography");
    const sans = within(typeSection).getByTestId("docs-type-sans");
    const mono = within(typeSection).getByTestId("docs-type-mono");
    expect(sans.style.fontFamily).toMatch(/var\(--font-sans\)/);
    expect(mono.style.fontFamily).toMatch(/var\(--font-mono\)/);
    expect(sans.textContent ?? "").toMatch(/\S/);
    expect(mono.textContent ?? "").toMatch(/\S/);
    expect(typeSection.textContent?.toLowerCase()).toContain("ibm plex sans");
    expect(typeSection.textContent?.toLowerCase()).toContain("ibm plex mono");
  });

  it("renders live component samples: button, stage chip, severity chips, card and phase strip", async () => {
    await renderDocs();
    const components = screen.getByTestId("docs-section-components");
    // live button sample painted with the accent token
    const button = within(components).getByTestId("docs-sample-button");
    expect(`${button.style.background} ${button.style.backgroundColor}`).toMatch(/var\(--color-accent\)/);
    // stage chip
    expect(within(components).getByTestId("docs-sample-stage-chip")).toBeInTheDocument();
    // severity/status chips, one per severity
    expect(within(components).getByTestId("docs-sample-severity-error")).toBeInTheDocument();
    expect(within(components).getByTestId("docs-sample-severity-warning")).toBeInTheDocument();
    expect(within(components).getByTestId("docs-sample-severity-info")).toBeInTheDocument();
    // card sample
    expect(within(components).getByTestId("docs-sample-card")).toBeInTheDocument();
    // phase strip with at least one dot and one label
    const strip = within(components).getByTestId("docs-sample-phase-strip");
    const dots = [
      ...Array.from(strip.querySelectorAll<HTMLElement>("[data-dot]")),
      ...Array.from(strip.querySelectorAll<HTMLElement>("[style]")).filter((el) =>
        /999|50%/.test(el.style.borderRadius || ""),
      ),
    ];
    expect(dots.length, "phase strip must show at least one phase dot").toBeGreaterThan(0);
    expect((strip.textContent ?? "").trim().length, "phase strip must show at least one phase label").toBeGreaterThan(0);
  });
});

describe("DocsPage drift guard — designTokens vs tokens.css (D10)", () => {
  // Source of truth: src/styles/tokens.css. Any hex edited in one place only
  // makes this test fail, so the docs page can never drift from the stylesheet.
  // Vite inlines the on-disk file content (?raw) at transform time.
  const TOKENS_CSS = import.meta.glob<string>("/src/styles/tokens.css", {
    query: "?raw",
    import: "default",
    eager: true,
  });
  const css = (Object.values(TOKENS_CSS)[0] ?? "").toLowerCase().replace(/\s+/g, "");
  it("defines its tokens in src/styles/tokens.css (every hex matches, on drift this fails)", () => {
    const list: DesignToken[] = DESIGN_TOKENS;
    expect(css, "tokens.css must be readable for the drift guard").toContain(":root");
    expect(list.length).toBeGreaterThanOrEqual(15);
    const required = [
      "--color-page",
      "--color-sidebar",
      "--color-card",
      "--color-inset",
      "--color-border",
      "--color-text-primary",
      "--color-text-secondary",
      "--color-text-tertiary",
      "--color-accent",
      "--color-accent-hover",
      "--color-on-accent",
      "--color-warn",
      "--color-info",
      "--color-design",
      "--color-danger",
    ];
    const cssVars = list.map((token) => token.cssVar);
    for (const cssVar of required) {
      expect(cssVars, `missing required token ${cssVar}`).toContain(cssVar);
    }
    for (const token of list) {
      expect(token.name, `${token.cssVar} must have a name`).toBeTruthy();
      expect(token.cssVar).toBeTruthy();
      expect(token.hex).toBeTruthy();
      expect(token.usage, `${token.cssVar} must document its usage`).toBeTruthy();
    }
    // every declared value (hex and the rgba border) must exist in tokens.css
    for (const token of list) {
      const value = token.hex.replace(/\s+/g, "").toLowerCase();
      expect(css, `${token.cssVar} = ${token.hex} must be defined in tokens.css`).toContain(value);
    }
  });
});

describe("DocsPage quickstart commands (D10 / REQ-009)", () => {
  it("renders each quickstart command in its own mono code block", async () => {
    await renderDocs();
    const quickstart = screen.getByTestId("docs-section-quickstart");
    const commands = ["docker compose up -d", "opensddrag-server init"];
    for (const cmd of commands) {
      const others = commands.filter((other) => other !== cmd);
      // "own block": a pre/code whose trimmed text is exactly this command
      const blocks = Array.from(quickstart.querySelectorAll("pre, code")).filter((el) => {
        const text = (el.textContent ?? "").trim();
        return text === cmd && !others.some((other) => text.includes(other));
      });
      expect(blocks.length, `expected a dedicated code block containing "${cmd}"`).toBeGreaterThan(0);
      const block = blocks[0] as HTMLElement;
      const pre = block.closest("pre") as HTMLElement | null;
      const fonts = [block.style.fontFamily, pre?.style.fontFamily, `${block.className} ${pre?.className ?? ""}`].join(" ");
      expect(fonts, `code block for "${cmd}" must reference var(--font-mono)`).toMatch(/var\(--font-mono\)|\bmono\b/);
    }
  });
});

describe("DocsPage getting-started (server, CLI, AI tools)", () => {
  it("documents Docker server setup, dashboard login, CLI init, Claude Code and OpenCode", async () => {
    await renderDocs();

    const server = screen.getByTestId("docs-section-server-setup");
    expect(server.textContent).toMatch(/docker compose up -d/);
    expect(server.textContent).toMatch(/MANAGEMENT_API_TOKEN/);
    expect(server.textContent).toMatch(/localhost:3001/);
    expect(server.textContent).toMatch(/localhost:8000/);

    const dashboard = screen.getByTestId("docs-section-dashboard");
    expect(dashboard.textContent).toMatch(/123456/);
    expect(dashboard.textContent).toMatch(/\/keys/);

    const cli = screen.getByTestId("docs-section-cli-client");
    expect(cli.textContent).toMatch(/npx opensddrag init/);
    expect(cli.textContent).toMatch(/--tools claude,opencode/);

    const claude = screen.getByTestId("docs-section-claude-code");
    expect(claude.textContent).toMatch(/\.mcp\.json/);
    expect(claude.textContent).toMatch(/Cursor/);
    expect(claude.textContent).toMatch(/\/opsr:propose/);
    expect(claude.textContent).toMatch(/Bearer <mcp-api-key>/);

    const opencode = screen.getByTestId("docs-section-opencode");
    expect(opencode.textContent).toMatch(/opencode\.json/);
    expect(opencode.textContent).toMatch(/type": "remote"/);
    expect(opencode.textContent).toMatch(/\.opencode\//);

    const keys = screen.getByTestId("docs-section-api-keys");
    expect(keys.textContent).toMatch(/opensddrag-server key create/);

    const pipelines = screen.getByTestId("docs-section-pipelines");
    expect(pipelines.textContent).toMatch(/register-flow/);
    expect(pipelines.textContent).toMatch(/\/opsr:<flow>:<command>/);
    expect(pipelines.textContent).toMatch(/add_rule currently accepts/);
    expect(pipelines.textContent).toMatch(/Built-in pipeline: SDD/);
    expect(pipelines.textContent).toMatch(/## Why/);
    expect(pipelines.textContent).toMatch(/required_headings/);
    expect(within(pipelines).getByTestId("docs-sdd-phases")).toBeInTheDocument();
    expect(within(pipelines).getByTestId("docs-kind-proposal")).toBeInTheDocument();
    expect(within(pipelines).getByTestId("docs-kind-spec")).toBeInTheDocument();
    expect(within(pipelines).getByTestId("docs-kind-design")).toBeInTheDocument();
    expect(within(pipelines).getByTestId("docs-kind-task")).toBeInTheDocument();
    expect(within(pipelines).getByTestId("docs-kind-test")).toBeInTheDocument();
    expect(screen.queryByTestId("docs-section-sdd-workflow")).not.toBeInTheDocument();
    expect(screen.queryByTestId("docs-section-artifact-formats")).not.toBeInTheDocument();

    const harness = screen.getByTestId("docs-section-harness-rules");
    expect(harness.textContent).toMatch(/tdd-first/);
    expect(harness.textContent).toMatch(/add_rule/);
  });
});