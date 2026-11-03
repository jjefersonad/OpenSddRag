import { useState, type FormEvent } from "react";
import { ApiError } from "../../api/client";
import { createKey, type CreatedApiKey } from "../../api/keys";
import type { Project } from "../../api/types";

interface Props {
  projects: Project[];
  onClose: () => void;
  onCreated: (created: CreatedApiKey) => void;
}

/** Create an MCP API key. The plaintext is returned only in this response. */
export default function CreateKeyModal({ projects, onClose, onCreated }: Props) {
  const [description, setDescription] = useState("");
  const [projectSlug, setProjectSlug] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const created = await createKey({
        description: description.trim(),
        project_slug: projectSlug || null,
        expires_at: expiresAt || null,
      });
      onCreated(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the key.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-key-title"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "grid",
        placeItems: "center",
        zIndex: 30,
      }}
    >
      <form
        onSubmit={onSubmit}
        style={{
          background: "var(--color-card)",
          border: "1px solid var(--color-border)",
          borderRadius: 12,
          padding: 24,
          width: 400,
          display: "grid",
          gap: 12,
        }}
      >
        <h2 id="create-key-title" style={{ margin: 0, fontSize: 16 }}>
          New API key
        </h2>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: 13, lineHeight: 1.5 }}>
          The plaintext is shown once after create. Use it as{" "}
          <code>Authorization: Bearer</code> on <code>/mcp</code>.
        </p>

        <label htmlFor="key-description" className="label">
          Description
        </label>
        <input
          id="key-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Cursor jeff_ai workspace"
        />

        <label htmlFor="key-scope" className="label">
          Scope
        </label>
        <select
          id="key-scope"
          value={projectSlug}
          onChange={(event) => setProjectSlug(event.target.value)}
        >
          <option value="">Global (all projects)</option>
          {projects.map((project) => (
            <option key={project.slug} value={project.slug}>
              {project.slug}
            </option>
          ))}
        </select>

        <label htmlFor="key-expires" className="label">
          Expires (optional)
        </label>
        <input
          id="key-expires"
          type="date"
          value={expiresAt}
          onChange={(event) => setExpiresAt(event.target.value)}
        />

        {error ? (
          <p role="alert" style={{ color: "var(--color-danger)", margin: 0 }}>
            {error}
          </p>
        ) : null}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
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
              borderRadius: 8,
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
