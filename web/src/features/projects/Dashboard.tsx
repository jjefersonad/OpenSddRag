import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../../api/client";
import { deleteProject } from "../../api/projects";
import type { Project } from "../../api/types";
import ConfirmDialog from "../../components/ConfirmDialog";
import { useProjects } from "../../hooks/useProjects";
import CreateProjectModal from "./CreateProjectModal";

/** Relative short time ("3h ago") from an ISO timestamp. */
export function relativeTime(iso?: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return "just now";
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  return `${Math.floor(d / 30)}mo ago`;
}

const PIPELINE_BAR = {
  done: "var(--color-accent)",
  active: "var(--color-accent-hover)",
  pending: "rgba(255,255,255,0.08)",
} as const;

const ACTION_BUTTON = {
  background: "transparent",
  border: "1px solid var(--color-border)",
  borderRadius: "6px",
  color: "var(--color-text-secondary)",
  fontSize: "12px",
  padding: "4px 8px",
  cursor: "pointer",
} as const;

/** One dashboard card (REQ-013): name, mono slug, stage chip (omitted when
 *  the flow declares no lifecycle), description, mini phase pipeline (one bar
 *  per phase, omitted when there are none), footer with language, relative
 *  time and `done/total tasks`. The card body links to the project. */
export function ProjectCard({
  project,
  onEdit,
  onDelete,
}: {
  project: Project;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const done = project.task_progress?.done ?? 0;
  const total = project.task_progress?.total ?? 0;
  const phases = project.phases ?? [];
  return (
    <li data-testid={`project-card-${project.slug}`} style={{ display: "flex" }}>
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          background: "var(--color-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "12px",
          padding: "20px",
          color: "var(--color-text-primary)",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px" }}>
          <Link to={`/p/${project.slug}`} style={{ minWidth: 0, color: "inherit", textDecoration: "none" }}>
            <div style={{ fontSize: "16px", fontWeight: 600 }}>{project.name}</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-text-tertiary)", marginTop: "3px" }}>
              {project.slug}
            </div>
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button type="button" onClick={onEdit} style={ACTION_BUTTON}>
              Edit
            </button>
            <button type="button" onClick={onDelete} style={{ ...ACTION_BUTTON, color: "var(--color-danger)" }}>
              Delete
            </button>
          {project.phase ? (
            <span
              data-testid={`stage-chip-${project.slug}`}
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--color-accent-hover)",
                background: "rgba(16,185,129,0.1)",
                border: "1px solid rgba(16,185,129,0.25)",
                borderRadius: "5px",
                padding: "3px 9px",
              }}
            >
              {project.phase}
            </span>
          ) : null}
          </div>
        </div>
        <Link
          to={`/p/${project.slug}`}
          style={{ display: "flex", flexDirection: "column", gap: "14px", flex: 1, color: "inherit", textDecoration: "none" }}
        >
        {project.description ? (
          <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "13.5px", lineHeight: 1.5 }}>
            {project.description}
          </p>
        ) : null}
        {phases.length > 0 ? (
          <div data-testid={`pipeline-${project.slug}`} style={{ display: "flex", gap: "4px", marginTop: "auto" }}>
            {phases.map((phase) => (
              <div
                key={phase.name}
                data-state={phase.status}
                title={phase.name}
                style={{ flex: 1, height: "3px", borderRadius: "2px", background: PIPELINE_BAR[phase.status] }}
              />
            ))}
          </div>
        ) : null}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontFamily: "var(--font-mono)",
            fontSize: "11.5px",
            color: "var(--color-text-tertiary)",
          }}
        >
          <span style={{ display: "flex", gap: "12px" }}>
            {project.language ? <span>{project.language}</span> : null}
            <span>{relativeTime(project.updated_at)}</span>
          </span>
          <span data-testid={`task-progress-${project.slug}`}>
            {done}/{total} tasks
          </span>
        </div>
        </Link>
      </div>
    </li>
  );
}

/** Project dashboard — header, 2-column grid of rich cards (REQ-013), empty
 *  state and create modal. */
export default function Dashboard() {
  const { projects, loading, error, reload } = useProjects();
  const location = useLocation();
  const navigate = useNavigate();
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Project | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const arrived = (location.state as { notice?: unknown } | null)?.notice;
  const [notice, setNotice] = useState<string | null>(null);
  useEffect(() => {
    if (typeof arrived !== "string") return;
    setNotice(arrived);
    navigate(location.pathname, { replace: true, state: null });
  }, [arrived, location.pathname, navigate]);

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    setDeleteError(null);
    const name = pendingDelete.name;
    try {
      await deleteProject(pendingDelete.slug);
      setPendingDelete(null);
      setNotice(`Project ${name} was deleted.`);
      reload();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Could not reach the API.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section>
      <header
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          marginBottom: "28px",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "28px", fontWeight: 700, letterSpacing: "-0.02em" }}>Projects</h1>
          <p style={{ margin: "6px 0 0", color: "var(--color-text-secondary)", fontSize: "14.5px" }}>
            {projects.length} registered · multi-tenant artifact memory
          </p>
        </div>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          style={{
            background: "var(--color-accent)",
            color: "var(--color-on-accent)",
            border: "none",
            borderRadius: "8px",
            padding: "12px 20px",
            fontWeight: 600,
            fontSize: "14px",
            cursor: "pointer",
          }}
        >
          + New project
        </button>
      </header>

      {notice ? (
        <p
          role="status"
          data-testid="project-notice"
          style={{
            margin: "0 0 16px",
            padding: "10px 12px",
            borderRadius: "8px",
            color: "var(--color-accent-hover)",
            background: "rgba(16,185,129,0.1)",
            border: "1px solid rgba(16,185,129,0.25)",
          }}
        >
          {notice}
        </p>
      ) : null}

      {loading ? <p>Loading…</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      {!loading && !error && projects.length === 0 ? (
        <div data-testid="dashboard-empty" style={{ color: "var(--color-text-secondary)" }}>
          No projects yet — create your first one to start a disciplined change.
        </div>
      ) : null}

      <ul className="dashboard-grid">
        {projects.map((project) => (
          <ProjectCard
            key={project.slug}
            project={project}
            onEdit={() => setEditing(project)}
            onDelete={() => {
              setDeleteError(null);
              setPendingDelete(project);
            }}
          />
        ))}
      </ul>

      {createOpen ? (
        <CreateProjectModal
          onClose={() => setCreateOpen(false)}
          onChanged={() => {
            setCreateOpen(false);
            reload();
          }}
        />
      ) : null}
      {editing ? (
        <CreateProjectModal
          project={editing}
          onClose={() => setEditing(null)}
          onChanged={() => {
            setEditing(null);
            reload();
          }}
        />
      ) : null}
      {pendingDelete ? (
        <ConfirmDialog
          title="Delete project"
          message={`Delete ${pendingDelete.name} and every artifact in it? This cannot be undone.`}
          confirmLabel="Delete"
          busy={deleting}
          error={deleteError}
          onClose={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
        />
      ) : null}
    </section>
  );
}