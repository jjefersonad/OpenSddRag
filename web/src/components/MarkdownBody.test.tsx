import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import MarkdownBody from "./MarkdownBody";

afterEach(() => cleanup());

describe("MarkdownBody", () => {
  it("renders headings, lists and emphasis instead of source markers", () => {
    render(
      <MarkdownBody>
        {"# Title\n\n## Problem Statement\n\nThe **system** SHALL:\n\n- Add a reader.\n- Keep Hierarchy a tree."}
      </MarkdownBody>,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Title" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Problem Statement" })).toBeInTheDocument();
    expect(screen.getByText("system").tagName).toBe("STRONG");
    expect(screen.getByText("Add a reader.")).toBeInTheDocument();
    expect(screen.queryByText(/^- Add a reader/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^# Title/)).not.toBeInTheDocument();
  });

  it("renders nothing for blank input", () => {
    const { container } = render(<MarkdownBody>{"   \n"}</MarkdownBody>);
    expect(container).toBeEmptyDOMElement();
  });
});
