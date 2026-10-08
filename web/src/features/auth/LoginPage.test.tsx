import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import LoginPage from "./LoginPage";
import { getToken } from "../../api/client";

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response;
}

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        {/* D1 route model: successful login lands on the dashboard at
            /projects — `/` is the public landing now. */}
        <Route path="/projects" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── Unit 2: LoginPage.submit (REQ-003) ──────────────────────────────────────

describe("LoginPage", () => {
  it("rejects an invalid token: nothing persisted, error shown, stays on login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(401, { error: { code: "UNAUTHORIZED", message: "bad" } }),
      ),
    );
    renderLogin();

    fireEvent.change(screen.getByLabelText(/token/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in|login|connect/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(getToken()).toBeNull();
    expect(screen.queryByText("Home")).not.toBeInTheDocument();
  });

  it("accepts a valid token: persists it and navigates to /", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, [])));
    renderLogin();

    fireEvent.change(screen.getByLabelText(/token/i), {
      target: { value: "good-token" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in|login|connect/i }));

    await waitFor(() => {
      expect(screen.getByText("Home")).toBeInTheDocument();
    });
    expect(getToken()).toBe("good-token");
  });
});