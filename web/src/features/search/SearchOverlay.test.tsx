import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import SearchOverlay from "./SearchOverlay";
import { setToken } from "../../api/client";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

function renderOverlay() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<SearchOverlay />} />
        <Route path="/p/:slug" element={<div>Detail</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
  setToken("t");
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── Unit 2: SearchOverlay keyboard (web-dashboard-ui REQ-005) ───────────────

describe("SearchOverlay", () => {
  it("opens with ⌘K, closes with Esc, and navigates on result selection", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(200, [
          { type: "spec", title: "harness-spec", snippet: "s", project: "opensddrag", score: 1, slug: "harness-spec" },
        ]),
      ),
    );
    renderOverlay();

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.keyDown(document, { key: "k", metaKey: true });
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "harness" } });
    const row = await screen.findByText("harness-spec");
    fireEvent.click(row);

    expect(await screen.findByText("Detail")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes on Escape", () => {
    renderOverlay();
    fireEvent.keyDown(document, { key: "k", metaKey: true });
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});