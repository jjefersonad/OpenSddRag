import { useState } from "react";
import { Link } from "react-router-dom";
import { useProjects } from "../../hooks/useProjects";
import CreateProjectModal from "./CreateProjectModal";
import type { Project } from "../../api/types";

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

/** One dashboard card (REQ-013): stage chip (when the flow declares a
 *  lifecycle — phase null omits it), description, language, relative
 *  updated time, aggregate task progress, mini phase pipeline. */
export function ProjectCard({ project }: { project: Project }) {
  const done = project.task_progress?.done ?? 0;
  const total = project.task_progress?.total ?? 0;
  return (
    <li
      data-testid={`project-card-${project.slug}`}
      style={{
        background: "var(--color-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "12px",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Link to={`/p/${project.slug}`} style={{ color: "var(--color-text-primary)", fontWeight: 600 }}>
          {project.name}
        </Link>
        {project.phase ? (
          <span
            data-testid={`stage-chip-${project.slug}`}
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "#34d399",
              background: "rgba(16,185,129,0.1)",
              border: "1px solid rgba(16,185,129,0.25)",
              borderRadius: "99px",
              padding: "2px 8px",
            }}
          >
            {project.phase}
          </span>
        ) : null}
      </div>
      {project.description ? (
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "13px" }}>
          {project.description}
        </p>
      ) : null}
      <div style={{ display: "flex", gap: "10px", alignItems: "center", fontFamily: "var(--font-mono)", fontSize: "11.5px", color: "var(--color-text-tertiary)" }}>
        {project.language ? <span>{project.language}</span> : null}
        <span>{relativeTime(project.updated_at)}</span>
        <span data-testid={`task-progress-${project.slug}`}>{done} / {total} tasks</span>
      </div>
    </li>
  );
}

/** Project dashboard — rich cards (REQ-013), empty state, create modal. */
export default function Dashboard() {
  const { projects, loading, error, reload } = useProjects();
  const [createOpen, setCreateOpen] = useState(false);

  return (
    <section>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "16px",
        }}
      >
        <h1 style={{ margin: 0, fontSize: "20px" }}>Projects</h1>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          style={{
            background: "var(--color-accent)",
            color: "var(--color-on-accent)",
            border: "none",
            borderRadius: "8px",
            padding: "8px 14px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          New project
        </button>
      </header>

      {loading ? <p>Loading…</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      {!loading && !error && projects.length === 0 ? (
        <div data-testid="dashboard-empty" style={{ color: "var(--color-text-secondary)" }}>
          No projects yet — create your first one to start a disciplined change.
        </div>
      ) : null}

      <ul
        style={{
          listStyle: "none",
          padding: 0,
          display: "grid",
          gap: "12px",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
        }}
      >
        {projects.map((project) => (
          <ProjectCard key={project.slug} project={project} />
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
    </section>
  );
}