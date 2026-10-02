import { useState, type FormEvent } from "react";
import { ApiError } from "../../api/client";
import { createProject } from "../../api/projects";

interface Props {
  onClose: () => void;
  onChanged: () => void;
}

function fieldMessages(details: unknown): string[] {
  if (!Array.isArray(details)) return [];
  return details
    .map((entry) =>
      entry && typeof entry === "object" && "msg" in entry
        ? String((entry as { msg: unknown }).msg)
        : null,
    )
    .filter((value): value is string => Boolean(value));
}

/** "New project" modal (REQ-006): duplicate slug → inline error, modal stays
 *  open; validation errors → field messages; success → onChanged. */
export default function CreateProjectModal({ onClose, onChanged }: Props) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [slugError, setSlugError] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSlugError(null);
    setErrors([]);
    setBusy(true);
    try {
      await createProject({ name, slug, description });
      onChanged();
    } catch (error) {
      if (error instanceof ApiError && error.code === "CONFLICT") {
        setSlugError("This slug already exists.");
      } else if (error instanceof ApiError && error.code === "VALIDATION_ERROR") {
        const messages = fieldMessages(error.details);
        setErrors(messages.length ? messages : [error.message]);
      } else if (error instanceof ApiError) {
        setSlugError(error.message);
      } else {
        setSlugError("Could not reach the API.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "grid",
        placeItems: "center",
      }}
    >
      <form
        onSubmit={onSubmit}
        style={{
          background: "var(--color-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "12px",
          padding: "24px",
          width: "380px",
          display: "grid",
          gap: "12px",
        }}
      >
        <h2 style={{ margin: 0, fontSize: "16px" }}>New project</h2>

        <label htmlFor="project-name" className="label">
          Name
        </label>
        <input
          id="project-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />

        <label htmlFor="project-slug" className="label">
          Slug
        </label>
        <input
          id="project-slug"
          value={slug}
          onChange={(event) => setSlug(event.target.value)}
        />
        {slugError ? (
          <p role="alert" style={{ color: "var(--color-danger)", margin: 0 }}>
            {slugError}
          </p>
        ) : null}

        <label htmlFor="project-description" className="label">
          Description
        </label>
        <input
          id="project-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />

        {errors.length ? (
          <ul role="alert" style={{ color: "var(--color-danger)", margin: 0 }}>
            {errors.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        ) : null}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
          <button type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            style={{
              background: "var(--color-accent)",
              color: "var(--color-on-accent)",
              border: "none",
              borderRadius: "8px",
              padding: "8px 14px",
              fontWeight: 600,
            }}
          >
            Create
          </button>
        </div>
      </form>
    </div>
  );
}
