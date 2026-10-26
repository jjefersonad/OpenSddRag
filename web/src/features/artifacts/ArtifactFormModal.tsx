import { useState, type FormEvent } from "react";
import { ApiError } from "../../api/client";
import { createArtifact, updateArtifact } from "../../api/artifacts";
import type { Artifact } from "../../api/types";

const STATUSES = ["draft", "active", "archived"];

interface Props {
  slug: string;
  type: string;
  artifact?: Artifact | null;
  changeName?: string;
  onClose: () => void;
  onSaved: () => void;
}

function messageOf(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Could not reach the API.";
}

/** Create or edit one artifact. Type is fixed by the tab or change section. */
export default function ArtifactFormModal({ slug, type, artifact, changeName, onClose, onSaved }: Props) {
  const editing = Boolean(artifact);
  const [name, setName] = useState(artifact?.name ?? "");
  const [content, setContent] = useState(artifact?.content ?? "");
  const [status, setStatus] = useState(artifact?.status ?? "draft");
  const initialChange =
    changeName ??
    (typeof artifact?.metadata?.change_name === "string" ? artifact.metadata.change_name : "");
  const [change, setChange] = useState(initialChange);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    const metadata = { ...(artifact?.metadata ?? {}), change_name: change };
    try {
      if (artifact) {
        await updateArtifact(artifact.id, { name, content, status, metadata });
      } else {
        await createArtifact(slug, { name, type, content, metadata });
      }
      onSaved();
    } catch (err) {
      setError(messageOf(err));
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
        zIndex: 30,
      }}
    >
      <form
        onSubmit={onSubmit}
        style={{
          background: "var(--color-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "12px",
          padding: "24px",
          width: "520px",
          maxWidth: "calc(100vw - 32px)",
          display: "grid",
          gap: "12px",
        }}
      >
        <h2 style={{ margin: 0, fontSize: "16px" }}>{editing ? `Edit ${type}` : `New ${type}`}</h2>
        <label htmlFor="artifact-name" className="label">
          Name
        </label>
        <input id="artifact-name" value={name} onChange={(event) => setName(event.target.value)} required />
        <label htmlFor="artifact-change" className="label">
          Change
        </label>
        <input id="artifact-change" value={change} onChange={(event) => setChange(event.target.value)} />
        {editing ? (
          <>
            <label htmlFor="artifact-status" className="label">
              Status
            </label>
            <select id="artifact-status" value={status} onChange={(event) => setStatus(event.target.value)}>
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </>
        ) : null}
        <label htmlFor="artifact-content" className="label">
          Content
        </label>
        <textarea
          id="artifact-content"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          rows={12}
          style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}
        />
        {error ? (
          <p role="alert" style={{ color: "var(--color-danger)", margin: 0 }}>
            {error}
          </p>
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
            {editing ? "Save" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}
