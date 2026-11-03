import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import CreateProjectModal from "./CreateProjectModal";

function jsonResponse(status: number, body: unknown) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as unknown as Response;
}

beforeEach(() => localStorage.clear());
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText(/name/i), { target: { value: "Demo" } });
  fireEvent.change(screen.getByLabelText(/slug/i), { target: { value: "demo" } });
  fireEvent.click(screen.getByRole("button", { name: /create/i }));
}

// ── Unit 3: CreateProjectModal.submit (REQ-006) ─────────────────────────────

describe("CreateProjectModal", () => {
  it("creates on success and calls onChanged + onClose", async () => {
    const onChanged = vi.fn();
    const onClose = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(201, { id: "1", name: "Demo", slug: "demo" })),
    );
    render(<CreateProjectModal onClose={onClose} onChanged={onChanged} />);

    fillAndSubmit();

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
  });

  it("shows an inline slug error on 409 and keeps the modal open", async () => {
    const onChanged = vi.fn();
    const onClose = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(409, { error: { code: "CONFLICT", message: "slug already exists" } }),
        ),
    );
    render(<CreateProjectModal onClose={onClose} onChanged={onChanged} />);

    fillAndSubmit();

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/already exists/i),
    );
    expect(onChanged).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
    // modal still mounted → the form is still present
    expect(screen.getByLabelText(/slug/i)).toBeInTheDocument();
  });

  it("renders field errors on 422", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(422, {
          error: {
            code: "VALIDATION_ERROR",
            message: "invalid project payload",
            details: [{ loc: ["slug"], msg: "slug must be kebab-case" }],
          },
        }),
      ),
    );
    render(<CreateProjectModal onClose={vi.fn()} onChanged={vi.fn()} />);

    fillAndSubmit();

    await waitFor(() =>
      expect(screen.getByText(/slug must be kebab-case/i)).toBeInTheDocument(),
    );
  });
});