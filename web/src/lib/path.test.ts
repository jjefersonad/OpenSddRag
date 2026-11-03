import { describe, expect, it } from "vitest";
import { projectSlugFromPath } from "./path";

describe("projectSlugFromPath (REQ-021)", () => {
  it("returns the first segment after /p/ even on a nested change URL", () => {
    expect(projectSlugFromPath("/p/opensddrag/c/web-change-reader")).toBe("opensddrag");
    expect(projectSlugFromPath("/p/opensddrag")).toBe("opensddrag");
  });

  it("returns null when the path is not a project URL", () => {
    expect(projectSlugFromPath("/projects")).toBeNull();
    expect(projectSlugFromPath("/")).toBeNull();
  });
});
