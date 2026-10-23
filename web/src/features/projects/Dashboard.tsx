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

const PIPELINE_BAR = {
  done: "var(--color-accent)",
  active: "var(--color-accent-hover)",
  pending: "rgba(255,255,255,0.08)",
} as const;

/** One dashboard card (REQ-013): name, mono slug, stage chip (omitted when
 *  the flow declares no lifecycle), description, mini phase pipeline (one bar
 *  per phase, omitted when there are none), footer with language, relative
 *  time and `done/total tasks`. The whole card links to the project. */
export function ProjectCard({ project }: { project: Project }) {
  const done = project.task_progress?.done ?? 0;
  const total = project.task_progress?.total ?? 0;
  const phases = project.phases ?? [];
  return (
    <li data-testid={`project-card-${project.slug}`} style={{ display: "flex" }}>
      <Link
        to={`/p/${project.slug}`}
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
          textDecoration: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px" }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: "16px", fontWeight: 600 }}>{project.name}</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-text-tertiary)", marginTop: "3px" }}>
              {project.slug}
            </div>
          </div>
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
    </li>
  );
}

/** Project dashboard — header, 2-column grid of rich cards (REQ-013), empty
 *  state and create modal. */
export default function Dashboard() {
  const { projects, loading, error, reload } = useProjects();
  const [createOpen, setCreateOpen] = useState(false);

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

      {loading ? <p>Loading…</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      {!loading && !error && projects.length === 0 ? (
        <div data-testid="dashboard-empty" style={{ color: "var(--color-text-secondary)" }}>
          No projects yet — create your first one to start a disciplined change.
        </div>
      ) : null}

      <ul className="dashboard-grid">
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