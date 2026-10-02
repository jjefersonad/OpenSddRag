import { useState } from "react";
import { Link } from "react-router-dom";
import { useProjects } from "../../hooks/useProjects";
import CreateProjectModal from "./CreateProjectModal";

/** Project dashboard — cards, empty state, and the "New project" modal. */
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
        <p style={{ color: "var(--color-text-secondary)" }}>
          No projects yet — create your first one.
        </p>
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
          <li
            key={project.slug}
            style={{
              background: "var(--color-card)",
              border: "1px solid var(--color-border)",
              borderRadius: "12px",
              padding: "16px",
            }}
          >
            <Link
              to={`/p/${project.slug}`}
              style={{ color: "var(--color-text-primary)", fontWeight: 600 }}
            >
              {project.name}
            </Link>
            <div className="slug" style={{ color: "var(--color-text-tertiary)" }}>
              {project.slug}
            </div>
          </li>
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
