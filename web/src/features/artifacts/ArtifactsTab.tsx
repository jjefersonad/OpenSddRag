import { useState } from "react";
import { ApiError } from "../../api/client";
import { deleteArtifact } from "../../api/artifacts";
import type { Artifact } from "../../api/types";
import ConfirmDialog from "../../components/ConfirmDialog";
import { useArtifacts } from "../../hooks/useArtifacts";
import ArtifactCard from "./ArtifactCard";
import ArtifactFormModal from "./ArtifactFormModal";
import GenericArtifactView from "./GenericArtifactView";
import SpecCard from "./SpecCard";
import { DesignView, ProposalView } from "./StructuredViews";
import { hasStructuredRenderer } from "./parsers";

const ACTION_BUTTON = {
  background: "transparent",
  border: "1px solid var(--color-border)",
  borderRadius: "6px",
  color: "var(--color-text-secondary)",
  fontSize: "12px",
  padding: "4px 8px",
  cursor: "pointer",
} as const;

/**
 * Renders a project's artifacts for one tab (filtered by type + flow,
 * web-api delta REQ-009). Dispatch (design D7): spec → full spec cards
 * (REQ-015); proposal/design → structured views; unknown kinds →
 * generic metadata+raw renderer.
 */
export default function ArtifactsTab({
  slug,
  type,
  flow,
  onChanged,
}: {
  slug: string;
  type?: string;
  flow?: string;
  onChanged?: () => void;
}) {
  // Structured SDD kinds need the body: request include=content in the
  // single list request (REQ-015) — no per-artifact getArtifact.
  const includeContent = type === "spec" || type === "proposal" || type === "design" || type === "test";
  const { artifacts, loading, error, reload } = useArtifacts(slug, type, flow, includeContent);
  const [editing, setEditing] = useState<Artifact | "new" | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Artifact | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const kind = type ?? "artifact";

  function saved() {
    setEditing(null);
    reload();
    onChanged?.();
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteArtifact(pendingDelete.id);
      setPendingDelete(null);
      reload();
      onChanged?.();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Could not reach the API.");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) return <p>Loading…</p>;
  if (error) return <p role="alert">{error}</p>;

  const visible = flow ? artifacts.filter((a) => (a.flow ?? "sdd") === flow) : artifacts;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <button type="button" onClick={() => setEditing("new")} style={{ ...ACTION_BUTTON, color: "var(--color-text-primary)" }}>
          New {kind}
        </button>
      </div>
      {visible.length === 0 ? <p>Nothing here yet.</p> : null}
      {visible.map((artifact) => (
        <div key={artifact.id} style={{ marginBottom: 10 }}>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 6 }}>
            <button type="button" onClick={() => setEditing(artifact)} style={ACTION_BUTTON}>
              Edit
            </button>
            <button type="button" onClick={() => { setDeleteError(null); setPendingDelete(artifact); }} style={{ ...ACTION_BUTTON, color: "var(--color-danger)" }}>
              Delete
            </button>
          </div>
          <ArtifactBody artifact={artifact} />
        </div>
      ))}
      {editing ? (
        <ArtifactFormModal
          slug={slug}
          type={editing === "new" ? kind : editing.type}
          artifact={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={saved}
        />
      ) : null}
      {pendingDelete ? (
        <ConfirmDialog
          title={`Delete ${kind}`}
          message={`Delete ${pendingDelete.name}? This cannot be undone.`}
          confirmLabel="Delete"
          busy={deleting}
          error={deleteError}
          onClose={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
        />
      ) : null}
    </div>
  );
}

function ArtifactBody({ artifact }: { artifact: Artifact }) {
  const kind = artifact.type;
  if (kind === "spec") return <SpecCard artifact={artifact} />;
  if (kind === "proposal") return <ProposalView artifact={artifact} />;
  if (kind === "design") return <DesignView artifact={artifact} />;
  if (hasStructuredRenderer(kind)) return <ArtifactCard artifact={artifact} />;
  return <GenericArtifactView artifact={artifact} />;
}