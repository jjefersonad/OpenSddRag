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

function renderPage() {
  render(
    <MemoryRouter>
      <KeysPage />
    </MemoryRouter>,
  );
}

describe("KeysPage list (REQ-017 / REQ-001 / REQ-004)", () => {
  it("renders heading, New key, filter, and one row per API record without secrets", async () => {
    mockApi((url) => {
      if (url.endsWith("/projects")) return jsonResponse(200, [{ id: "1", name: "Jeff", slug: "jeff-ai" }]);
      if (url.includes("/keys")) return jsonResponse(200, [sampleKey]);
      return jsonResponse(404, {});
    });
    renderPage();

    expect(await screen.findByRole("heading", { name: "API keys" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /new key/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/filter/i)).toBeInTheDocument();

    const row = await screen.findByTestId("key-row-fbe6f1ea");
    expect(within(row).getByText("Cursor jeff_ai")).toBeInTheDocument();
    expect(within(row).getByText("fbe6f1ea")).toBeInTheDocument();
    expect(within(row).getByText("jeff-ai")).toBeInTheDocument();
    expect(within(row).getByText("2026-10-25")).toBeInTheDocument();
    expect(within(row).getByText("active")).toBeInTheDocument();
    expect(screen.queryByText(/key_hash/i)).not.toBeInTheDocument();
    expect(screen.queryByText("plain-once-secret")).not.toBeInTheDocument();
    expect(screen.getAllByTestId(/key-row-/)).toHaveLength(1);
  });

  it("shows the empty state when the API returns no keys", async () => {
    mockApi((url) => {
      if (url.endsWith("/projects")) return jsonResponse(200, []);
      if (url.includes("/keys")) return jsonResponse(200, []);
      return jsonResponse(404, {});
    });
    renderPage();
    expect(await screen.findByText("No API keys.")).toBeInTheDocument();
    expect(screen.queryByTestId("keys-table")).not.toBeInTheDocument();
  });

  it("shows an error when the list request fails", async () => {
    mockApi((url) => {
      if (url.endsWith("/projects")) return jsonResponse(200, []);
      if (url.includes("/keys")) {
        return jsonResponse(500, { error: { code: "INTERNAL", message: "keys unavailable" } });
      }
      return jsonResponse(404, {});
    });
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("keys unavailable");
    expect(screen.queryByTestId("keys-table")).not.toBeInTheDocument();
  });

  it("maps All / Global / project filters onto the list query", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      const href = String(url);
      if (href.endsWith("/projects")) return jsonResponse(200, [{ id: "1", name: "Jeff", slug: "jeff-ai" }]);
      if (href.includes("/keys")) return jsonResponse(200, []);
      return jsonResponse(404, {});
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPage();
    await screen.findByText("No API keys.");

    fireEvent.change(screen.getByLabelText(/filter/i), { target: { value: "global" } });
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes("scope=global"))).toBe(true);
    });

    fireEvent.change(screen.getByLabelText(/filter/i), { target: { value: "jeff-ai" } });
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes("project=jeff-ai"))).toBe(true);
    });

    fireEvent.click(screen.getByLabelText(/show revoked/i));
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([url]) => String(url).includes("project=jeff-ai") && String(url).includes("include_revoked=true"),
        ),
      ).toBe(true);
    });
  });
});

describe("KeysPage create reveal (REQ-017 / REQ-002)", () => {
  it("POSTs /keys then closes the modal and shows the plaintext once with a warning", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      const href = String(url);
      if (href.endsWith("/projects")) return jsonResponse(200, [{ id: "1", name: "Jeff", slug: "jeff-ai" }]);
      if (href.includes("/keys") && init?.method === "POST") {
        return jsonResponse(201, { ...sampleKey, key: "plain-once-secret" });
      }
      if (href.includes("/keys")) return jsonResponse(200, [sampleKey]);
      return jsonResponse(404, {});
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /new key/i }));
    expect(screen.getByRole("dialog", { name: /new api key/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/description/i), { target: { value: "Cursor jeff_ai" } });
    fireEvent.click(screen.getByRole("button", { name: /^create$/i }));

    expect(await screen.findByTestId("created-key")).toHaveTextContent("plain-once-secret");
    expect(screen.queryByRole("dialog", { name: /new api key/i })).not.toBeInTheDocument();
    expect(screen.getByTestId("key-reveal")).toHaveTextContent(/will not be shown again/i);
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) => String(url).endsWith("/keys") && init?.method === "POST",
      ),
    ).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: /^done$/i }));
    expect(screen.queryByTestId("created-key")).not.toBeInTheDocument();
    expect(screen.queryByText("plain-once-secret")).not.toBeInTheDocument();
  });
});

describe("KeysPage", () => {
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
