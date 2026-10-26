import { describe, expect, it } from "vitest";
import KeysPage from "./features/keys/KeysPage";
import ProjectDetail from "./features/projects/ProjectDetail";
import { routes } from "./routes";

describe("project routes (REQ-021)", () => {
  it("defines c/:change as a child of /p/:slug rendering ProjectDetail", () => {
    const project = routes.find((route) => route.path === "/p/:slug");
    expect(project).toBeDefined();
    const child = project?.children?.find((entry) => entry.path === "c/:change");
    expect(child).toBeDefined();
    expect(child?.element).toMatchObject({ type: ProjectDetail });
    const index = project?.children?.find((entry) => entry.index);
    expect(index?.element).toMatchObject({ type: ProjectDetail });
  });
});

describe("keys route", () => {
  it("mounts KeysPage at /keys", () => {
    const keys = routes.find((route) => route.path === "/keys");
    expect(keys).toBeDefined();
    expect(keys?.children?.[0]?.element).toMatchObject({ type: KeysPage });
  });
});
