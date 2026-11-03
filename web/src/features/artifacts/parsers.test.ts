import { describe, expect, it } from "vitest";
import { briefTitle, displayTitle } from "./parsers";

describe("displayTitle (change-reader REQ-001)", () => {
  it("uses the first Why paragraph of a proposal, not the slug", () => {
    const title = displayTitle({
      type: "proposal",
      name: "web-change-reader-proposal",
      changeName: "web-change-reader",
      content: [
        "# web-change-reader",
        "",
        "## Why",
        "A human cannot read what a change did",
        "",
        "## What Changes",
        "- Add a reader.",
      ].join("\n"),
    });
    expect(title).toBe("A human cannot read what a change did");
    expect(title).not.toContain("web-change-reader-proposal");
  });

  it("uses the first Goal paragraph of a task, not the task slug", () => {
    const title = displayTitle({
      type: "task",
      name: "web-change-reader-task-domain-1",
      changeName: "web-change-reader",
      content: "## Goal\nPure domain module for change progress\n\n## Steps\n- Write it.",
    });
    expect(title).toBe("Pure domain module for change progress");
    expect(title).not.toContain("web-change-reader-task-domain-1");
  });

  it("falls back to a cleaned slug and never returns an empty title", () => {
    const title = displayTitle({
      type: "task",
      name: "web-change-reader-task-domain-1",
      changeName: "web-change-reader",
      content: "# task\n\nNo heading here.",
    });
    expect(title).toBe("domain-1");
    expect(title.length).toBeGreaterThan(0);
  });

  it("briefTitle keeps a short sentence and truncates a long Why", () => {
    expect(briefTitle("A human cannot read what a change did")).toBe(
      "A human cannot read what a change did",
    );
    const long =
      "Em produção, quando o usuário pede uma tarefa mais longa ao agente no chat web, o navegador registra um erro de rede e a tela mostra falha.";
    const brief = briefTitle(long, 90);
    expect(brief.length).toBeLessThanOrEqual(90);
    expect(brief.endsWith("…")).toBe(true);
  });
});
