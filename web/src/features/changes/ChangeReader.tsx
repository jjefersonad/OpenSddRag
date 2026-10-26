import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { deleteArtifact } from "../../api/artifacts";
import { getChangeBundle, type ChangeBundle, type ChangeSummary, type ChangeTask } from "../../api/changes";
import type { Artifact } from "../../api/types";
import ConfirmDialog from "../../components/ConfirmDialog";
import ArtifactFormModal from "../artifacts/ArtifactFormModal";
import { DesignView, ProposalView } from "../artifacts/StructuredViews";
import SpecCard from "../artifacts/SpecCard";
import TaskRow from "../artifacts/TaskRow";
import { briefTitle, displayTitle } from "../artifacts/parsers";
import {
  changeStage,
  formatChangeDate,
  humanizeChangeName,
  stageColor,
  taskProgressLabel,
} from "../projects/changeList";

const SECTION_LABEL = {
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  letterSpacing: "0.09em",
  textTransform: "uppercase" as const,
  color: "#5b6469",
  marginBottom: 14,
};

function taskAsArtifact(task: ChangeTask, change: string): Artifact {
  return {
    id: task.id ?? task.name,
    name: task.name,
    type: "task",
    status: task.status,
    content: task.content,
    metadata: { done: task.done, change_name: change },
  };
}

function sectionTitle(kind: "proposal" | "spec" | "design", artifact: Artifact, change: string): string {
  return briefTitle(
    displayTitle({
      type: kind,
      name: artifact.name,
      content: artifact.content,
      changeName: change,
    }),
  );
}

/** One-change document: briefing, then proposal → specs → design → tasks.
 *  `stageKinds` limits the body to the lifecycle kinds of one phase.
 *  `null` shows the whole change. An empty list is a phase with no artifacts. */
export default function ChangeReader({
  slug,
  change,
  summary,
  stageKinds = null,
  onChanged,
}: {
  slug: string;
  change: string;
  summary?: ChangeSummary | null;
  stageKinds?: string[] | null;
  onChanged?: () => void;
}) {
  const [bundle, setBundle] = useState<ChangeBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [form, setForm] = useState<{ type: string; artifact: Artifact | null } | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Artifact | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let alive = true;
    setBundle(null);
    setError(null);
    getChangeBundle(slug, change)
      .then((data) => {
        if (alive) setBundle(data);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        if (err instanceof ApiError && err.code === "NOT_FOUND") {
          setError("Change not found.");
        } else {
          setError(err instanceof Error ? err.message : "failed to load change");
        }
      });
    return () => {
      alive = false;
    };
  }, [slug, change, refresh]);

  function saved() {
    setForm(null);
    setRefresh((value) => value + 1);
    onChanged?.();
  }

  async function confirmDelete() {
    if (!pendingDelete?.id) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteArtifact(pendingDelete.id);
      setPendingDelete(null);
      setRefresh((value) => value + 1);
      onChanged?.();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Could not reach the API.");
    } finally {
      setDeleting(false);
    }
  }

  if (error) return <p role="alert">{error}</p>;
  if (!bundle) return <p>Loading…</p>;

  const done = bundle.tasks.filter((task) => task.done).length;
  const total = bundle.task_count;
  const stage = summary ? changeStage(summary) : null;
  const filtering = stageKinds !== null;
  const show = (kind: string) => !filtering || stageKinds.includes(kind);
  const anySection = show("proposal") || show("spec") || show("design") || show("task");

  return (
    <article data-testid="change-reader" style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      <header data-testid="change-briefing" style={{ paddingBottom: 4, borderBottom: "1px solid var(--color-border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 8 }}>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 650, letterSpacing: "-0.02em" }}>
            {humanizeChangeName(change)}
          </h2>
          {stage ? (
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                padding: "3px 8px",
                borderRadius: 6,
                color: stageColor(stage),
                border: `1px solid ${stageColor(stage)}44`,
              }}
            >
              {stage}
            </span>
          ) : null}
        </div>
        <p style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: 12, color: "#8a9298" }}>
          {change}
          {summary ? ` · started ${formatChangeDate(summary.started_at ?? summary.updated_at)}` : null}
          {` · ${taskProgressLabel({ done, total })} tasks`}
        </p>
      </header>

      {filtering && !anySection ? (
        <p data-testid="stage-empty" style={{ margin: 0, color: "var(--color-text-tertiary)", fontSize: 13 }}>
          Nothing in this stage yet.
        </p>
      ) : null}

      {show("proposal") ? (
      <section>
        <SectionHeading
          label="Proposal"
          onNew={() => setForm({ type: "proposal", artifact: null })}
          newLabel="New proposal"
          artifact={bundle.proposal}
          onEdit={() => bundle.proposal && setForm({ type: "proposal", artifact: bundle.proposal })}
          onDelete={() => bundle.proposal && setPendingDelete(bundle.proposal)}
        />
        {bundle.proposal ? (
          <>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 600, color: "#e8ebed" }}>
              {sectionTitle("proposal", bundle.proposal, change)}
            </h3>
            <ProposalView artifact={bundle.proposal} />
          </>
        ) : (
          <p style={{ color: "var(--color-text-tertiary)", fontSize: 13 }}>No proposal yet</p>
        )}
      </section>
      ) : null}

      {show("spec") ? (
      <section>
        <SectionHeading label="Specs" onNew={() => setForm({ type: "spec", artifact: null })} newLabel="New spec" />
        {bundle.specs.length === 0 ? (
          <p style={{ color: "var(--color-text-tertiary)", fontSize: 13 }}>No specs yet</p>
        ) : (
          bundle.specs.map((spec) => (
            <div key={spec.id ?? spec.name}>
              <RowActions
                onEdit={() => setForm({ type: "spec", artifact: spec })}
                onDelete={() => setPendingDelete(spec)}
              />
              <SpecCard artifact={spec} title={sectionTitle("spec", spec, change)} />
            </div>
          ))
        )}
      </section>
      ) : null}

      {show("design") ? (
      <section>
        <SectionHeading
          label="Design"
          onNew={() => setForm({ type: "design", artifact: null })}
          newLabel="New design"
          artifact={bundle.design}
          onEdit={() => bundle.design && setForm({ type: "design", artifact: bundle.design })}
          onDelete={() => bundle.design && setPendingDelete(bundle.design)}
        />
        {bundle.design ? (
          <>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 600, color: "#e8ebed" }}>
              {sectionTitle("design", bundle.design, change)}
            </h3>
            <DesignView artifact={bundle.design} />
          </>
        ) : (
          <p style={{ color: "var(--color-text-tertiary)", fontSize: 13 }}>No design yet</p>
        )}
      </section>
      ) : null}

      {show("task") ? (
      <section>
        <div style={{ ...SECTION_LABEL, display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <span>Tasks</span>
          <span style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span data-testid="reader-task-progress" style={{ letterSpacing: 0, textTransform: "none", color: "#8a9298" }}>
              {done}/{total} done
            </span>
            <button type="button" onClick={() => setForm({ type: "task", artifact: null })} style={ACTION_BUTTON}>
              New task
            </button>
          </span>
        </div>
        {bundle.tasks.length === 0 ? (
          <p style={{ color: "var(--color-text-tertiary)", fontSize: 13 }}>No tasks yet</p>
        ) : (
          bundle.tasks.map((task) => {
            const artifact = taskAsArtifact(task, change);
            return (
              <div key={task.id ?? task.name}>
                <RowActions
                  onEdit={() => setForm({ type: "task", artifact })}
                  onDelete={() => setPendingDelete(artifact)}
                />
                <TaskRow slug={slug} task={artifact} readOnly />
              </div>
            );
          })
        )}
      </section>
      ) : null}
      {form ? (
        <ArtifactFormModal
          slug={slug}
          type={form.type}
          artifact={form.artifact}
          changeName={change}
          onClose={() => setForm(null)}
          onSaved={saved}
        />
      ) : null}
      {pendingDelete ? (
        <ConfirmDialog
          title={`Delete ${pendingDelete.type}`}
          message={`Delete ${pendingDelete.name}? This cannot be undone.`}
          confirmLabel="Delete"
          busy={deleting}
          error={deleteError}
          onClose={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
        />
      ) : null}
    </article>
  );
}

const ACTION_BUTTON = {
  background: "transparent",
  border: "1px solid var(--color-border)",
  borderRadius: "6px",
  color: "var(--color-text-secondary)",
  fontSize: "12px",
  padding: "4px 8px",
  cursor: "pointer",
} as const;

function RowActions({ onEdit, onDelete }: { onEdit: () => void; onDelete: () => void }) {
  return (
    <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 6 }}>
      <button type="button" onClick={onEdit} style={ACTION_BUTTON}>
        Edit
      </button>
      <button type="button" onClick={onDelete} style={{ ...ACTION_BUTTON, color: "var(--color-danger)" }}>
        Delete
      </button>
    </div>
  );
}

function SectionHeading({
  label,
  newLabel,
  onNew,
  artifact,
  onEdit,
  onDelete,
}: {
  label: string;
  newLabel: string;
  onNew: () => void;
  artifact?: Artifact | null;
  onEdit?: () => void;
  onDelete?: () => void;
}) {
  return (
    <div style={{ ...SECTION_LABEL, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span>{label}</span>
      <span style={{ display: "flex", gap: 8 }}>
        {artifact && onEdit && onDelete ? <RowActions onEdit={onEdit} onDelete={onDelete} /> : null}
        <button type="button" onClick={onNew} style={ACTION_BUTTON}>
          {newLabel}
        </button>
      </span>
    </div>
  );
}
