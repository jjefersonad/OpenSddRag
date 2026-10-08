import { startTransition, useEffect, useState } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import SearchOverlay from "./features/search/SearchOverlay";
import { listProjects } from "./api/projects";
import { clearToken } from "./api/client";
import type { Project } from "./api/types";
import "./styles/base.css";

/**
 * Authenticated app shell (design D2, REQ-012): fixed left sidebar with the
 * logo, the docs link, the project list and the sign-out control; routed
 * content on the right; ⌘K search overlay lives in the shell.
 */

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    let alive = true;
    listProjects().then(
      (items) => {
        if (alive) setProjects(items);
      },
      () => {
        if (alive) setProjects([]);
      },
    );
    return () => {
      alive = false;
    };
  }, []);

  function signOut() {
    clearToken();
    startTransition(() => navigate("/", { replace: true }));
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "220px 1fr",
        minHeight: "100%",
        background: "var(--color-page)",
      }}
    >
      <aside
        data-testid="app-sidebar"
        style={{
          background: "var(--color-sidebar)",
          borderRight: "1px solid var(--color-border)",
          padding: "20px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-mono)",
            color: "var(--color-accent)",
            fontWeight: 600,
          }}
        >
          OpenSddRag
        </span>
        <Link to="/docs" style={{ color: "var(--color-text-secondary)" }}>
          Docs &amp; design system
        </Link>
        <nav aria-label="Projects" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {projects.map((p) => (
            <Link key={p.slug} to={`/p/${p.slug}`} style={{ color: "var(--color-text)" }}>
              {p.name}
            </Link>
          ))}
        </nav>
        <button type="button" onClick={signOut} style={{ marginTop: "auto", textAlign: "left" }}>
          Sign out
        </button>
      </aside>
      <main style={{ padding: "24px" }}>
        <Outlet />
      </main>
      <SearchOverlay />
    </div>
  );
}