import { describe, expect, it } from "vitest";
import indexHtml from "../../index.html?raw";
import baseCss from "./base.css?raw";
import tokensCss from "./tokens.css?raw";

/**
 * web-ui-prototype-fidelity — REQ-017 (typography + base reset) and the grid
 * class contract consumed by the dashboard / overview (design D8, D9).
 */

describe("index.html fonts (REQ-017)", () => {
  it("loads IBM Plex Sans and Mono from Google Fonts with display=swap", () => {
    expect(indexHtml).toContain("fonts.googleapis.com/css2");
    expect(indexHtml).toContain("family=IBM+Plex+Sans");
    expect(indexHtml).toContain("family=IBM+Plex+Mono");
    expect(indexHtml).toContain("display=swap");
    expect(indexHtml).toContain('rel="preconnect"');
  });

  it("keeps the token fallback stack for offline rendering", () => {
    expect(tokensCss).toMatch(/--font-sans:\s*"IBM Plex Sans",\s*system-ui/);
    expect(tokensCss).toMatch(/--font-mono:\s*"IBM Plex Mono",\s*ui-monospace/);
  });
});

describe("base.css reset and layout classes (REQ-017)", () => {
  const compact = baseCss.replace(/\s+/g, " ");

  it("resets anchors so no default blue/underline leaks", () => {
    expect(compact).toMatch(/a \{[^}]*color: inherit/);
    expect(compact).toMatch(/a \{[^}]*text-decoration: none/);
  });

  it("sets box-sizing, form font inheritance and scrollbar/selection styling", () => {
    expect(compact).toContain("box-sizing: border-box");
    expect(compact).toMatch(/input,\s*textarea,\s*button,\s*select \{[^}]*font-family: inherit/);
    expect(compact).toContain("::selection");
    expect(compact).toContain("::-webkit-scrollbar");
  });

  it("defines the responsive grid classes with their breakpoints", () => {
    expect(compact).toMatch(/\.dashboard-grid \{/);
    expect(compact).toMatch(/@media \(min-width: 960px\) \{[^@]*\.dashboard-grid[^}]*repeat\(2/);
    expect(compact).toMatch(/\.overview-grid \{/);
    expect(compact).toMatch(/@media \(min-width: 1100px\) \{[^@]*\.overview-grid[^}]*460px/);
  });

  it("never hides content behind an entry animation (guide section 8)", () => {
    expect(compact).not.toMatch(/animation-fill-mode:\s*both/);
    expect(compact).not.toMatch(/animation:[^;}]*\bboth\b/);
  });
});
