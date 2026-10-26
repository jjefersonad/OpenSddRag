import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import KeysPage from "./KeysPage";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

beforeEach(() => {
  localStorage.setItem("opensddrag.management_token", "t");
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function mockApi(handler: (url: string, init?: RequestInit) => Response) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => handler(String(url), init)),
  );
}

const sampleKey = {
  id: "k1",
  prefix: "fbe6f1ea",
  description: "Cursor jeff_ai",
  project_slug: "jeff-ai",
  created_at: "2026-10-25T12:00:00+00:00",
  expires_at: null,
  revoked_at: null,
  status: "active",
};

describe("KeysPage", () => {
  it("lists keys and reveals the plaintext once after create", async () => {
    mockApi((url, init) => {
      if (url.endsWith("/projects")) return jsonResponse(200, [{ id: "1", name: "Jeff", slug: "jeff-ai" }]);
      if (url.includes("/keys") && init?.method === "POST") {
        return jsonResponse(201, { ...sampleKey, key: "plain-once-secret" });
      }
      if (url.includes("/keys")) return jsonResponse(200, [sampleKey]);
      return jsonResponse(404, {});
    });

    render(
      <MemoryRouter>
        <KeysPage />
      </MemoryRouter>,
    );

    const row = await screen.findByTestId("key-row-fbe6f1ea");
    expect(within(row).getByText("jeff-ai")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /new key/i }));
    fireEvent.change(screen.getByLabelText(/description/i), { target: { value: "Cursor jeff_ai" } });
    fireEvent.click(screen.getByRole("button", { name: /^create$/i }));

    expect(await screen.findByTestId("created-key")).toHaveTextContent("plain-once-secret");
  });

  it("revokes after confirm", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).endsWith("/projects")) return jsonResponse(200, []);
      if (String(url).includes("/revoke")) return jsonResponse(200, { ...sampleKey, status: "revoked" });
      return jsonResponse(200, [sampleKey]);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter>
        <KeysPage />
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: /revoke/i }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: /^revoke$/i }));
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url, init]) => String(url).includes("/revoke") && init?.method === "POST")).toBe(
        true,
      );
    });
  });
});
