import { useState } from "react";
import { ApiError } from "../../api/client";
import { deleteArtifact } from "../../api/artifacts";
import type { Artifact } from "../../api/types";
import ConfirmDialog from "../../components/ConfirmDialog";
import { useArtifacts } from "../../hooks/useArtifacts";
import ArtifactFormModal from "./ArtifactFormModal";
import TaskRow from "./TaskRow";

const ACTION_BUTTON = {
  background: "transparent",
  border: "1px solid var(--color-border)",
  borderRadius: "6px",
  color: "var(--color-text-secondary)",
  fontSize: "12px",
  padding: "4px 8px",
  cursor: "pointer",
} as const;

/** Tasks tab: task artifacts rendered as optimistic checkboxes. */
export default function TaskList({ slug, onChanged }: { slug: string; onChanged?: () => void }) {
  const { artifacts, loading, error, reload } = useArtifacts(slug, "task", undefined, true);
  const [editing, setEditing] = useState<Artifact | "new" | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Artifact | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

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

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <button type="button" onClick={() => setEditing("new")} style={{ ...ACTION_BUTTON, color: "var(--color-text-primary)" }}>
          New task
        </button>
      </div>
      {artifacts.length === 0 ? <p>No tasks yet.</p> : null}
      {artifacts.map((task) => (
        <div key={task.id}>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <button type="button" onClick={() => setEditing(task)} style={ACTION_BUTTON}>
              Edit
            </button>
            <button type="button" onClick={() => { setDeleteError(null); setPendingDelete(task); }} style={{ ...ACTION_BUTTON, color: "var(--color-danger)" }}>
              Delete
            </button>
          </div>
          <TaskRow slug={slug} task={task} />
        </div>
      ))}
      {editing ? (
        <ArtifactFormModal
          slug={slug}
          type="task"
          artifact={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={saved}
        />
      ) : null}
      {pendingDelete ? (
        <ConfirmDialog
          title="Delete task"
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
