import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import SearchOverlay from "./features/search/SearchOverlay";
import { listProjects } from "./api/projects";
import { clearToken } from "./api/client";
import type { Project } from "./api/types";
import { projectSlugFromPath } from "./lib/path";
import "./styles/base.css";

/**
 * Authenticated app shell (design D2, REQ-012) — visual grammar from the
 * prototype: fixed 228px sidebar with nav items (Projects active-state,
 * Search + ⌘K badge that opens the overlay, Docs & design system), the
 * PROJECTS section with dot-coloured items (green highlights the current
 * one), and the pulsing "MCP server · :8000" footer.
 */

/** Global open-request for the ⌘K overlay (sidebar button → overlay). */
export function openSearchOverlay() {
  window.dispatchEvent(new CustomEvent("opsr:open-search"));
}

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const navigate = useNavigate();
  const location = useLocation();
  const activeSlug = projectSlugFromPath(location.pathname);
  const isDashboard = location.pathname === "/projects" || location.pathname.startsWith("/projects/");
  const isKeys = location.pathname === "/keys" || location.pathname.startsWith("/keys/");

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
    navigate("/", { replace: true });
  }

  return (
    <div style={{ display: "flex", minHeight: "100%", background: "var(--color-page)" }}>
      <aside
        data-testid="app-sidebar"
        style={{
          width: "228px",
          flexShrink: 0,
          background: "var(--color-sidebar)",
          borderRight: "1px solid rgba(255,255,255,0.07)",
          display: "flex",
          flexDirection: "column",
          position: "sticky",
          top: 0,
          height: "100vh",
        }}
      >
        <Link
          to="/projects"
          style={{
            padding: "18px",
            display: "flex",
            alignItems: "center",
            gap: 10,
            borderBottom: "1px solid rgba(255,255,255,0.06)",
            textDecoration: "none",
          }}
        >
          <span style={{ width: 28, height: 28, borderRadius: 7, background: "var(--color-accent)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-mono)", fontWeight: 600, color: "#04140d", fontSize: 14 }}>
            ⌘
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, fontSize: 14, color: "var(--color-text)" }}>
            OpenSddRag
          </span>
        </Link>

        <div style={{ padding: "14px 12px", flex: 1, display: "flex", flexDirection: "column", gap: 3 }}>
          <Link
            to="/projects"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 11,
              padding: "9px 12px",
              borderRadius: 8,
              cursor: "pointer",
              fontSize: 14,
              textDecoration: "none",
              background: isDashboard ? "rgba(16,185,129,0.1)" : "transparent",
              color: isDashboard ? "#34d399" : "#cdd3d7",
            }}
          >
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, width: 16 }}>▤</span> Projects
          </Link>

          <button
            type="button"
            data-testid="sidebar-search"
            onClick={openSearchOverlay}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "9px 12px",
              borderRadius: 8,
              cursor: "pointer",
              fontSize: 14,
              color: "#8a9298",
              background: "transparent",
              border: "none",
              textAlign: "left",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 11 }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, width: 16 }}>⌕</span> Search
            </span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#5b6469", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4, padding: "1px 5px" }}>
              ⌘K
            </span>
          </button>

          <Link
            to="/keys"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 11,
              padding: "9px 12px",
              borderRadius: 8,
              cursor: "pointer",
              fontSize: 14,
              textDecoration: "none",
              background: isKeys ? "rgba(16,185,129,0.1)" : "transparent",
              color: isKeys ? "#34d399" : "#cdd3d7",
            }}
          >
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, width: 16 }}>⚿</span> API keys
          </Link>

          <Link
            to="/docs"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 11,
              padding: "9px 12px",
              borderRadius: 8,
              cursor: "pointer",
              fontSize: 14,
              textDecoration: "none",
              color: "#cdd3d7",
            }}
          >
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, width: 16 }}>◆</span> Docs &amp; design system
          </Link>

          <div
            style={{
              marginTop: 18,
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "#4d565b",
              padding: "0 12px 8px",
            }}
          >
            Projects
          </div>

          {projects.map((p) => {
            const isActive = activeSlug === p.slug;
            return (
              <Link
                key={p.slug}
                to={`/p/${p.slug}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 9,
                  padding: "7px 12px",
                  borderRadius: 7,
                  cursor: "pointer",
                  fontSize: 13,
                  textDecoration: "none",
                  color: isActive ? "#34d399" : "#9aa2a8",
                  background: isActive ? "rgba(16,185,129,0.1)" : "transparent",
                }}
              >
                <span style={{ width: 7, height: 7, borderRadius: 99, flexShrink: 0, background: isActive ? "#34d399" : "#2b3238" }} />
                <span style={{ fontFamily: "var(--font-mono)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {p.slug}
                </span>
              </Link>
            );
          })}
        </div>

        <div
          style={{
            padding: "14px 18px",
            borderTop: "1px solid rgba(255,255,255,0.06)",
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            color: "#6b747a",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span style={{ width: 7, height: 7, borderRadius: 99, background: "#34d399", animation: "pulseDot 2.4s infinite" }} />
          <span>MCP server · :8000</span>
          <button
            type="button"
            onClick={signOut}
            aria-label="Sign out"
            style={{
              marginLeft: "auto",
              background: "transparent",
              border: "none",
              color: "#8a9298",
              cursor: "pointer",
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              padding: 0,
            }}
          >
            ⏻
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        {/* topbar — translucent, breadcrumb left, semantic search button right */}
        <div
          style={{
            height: 56,
            flexShrink: 0,
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 26px",
            background: "rgba(10,12,13,0.7)",
            position: "sticky",
            top: 0,
            zIndex: 20,
          }}
        >
          <div data-testid="app-breadcrumb" style={{ display: "flex", alignItems: "center", gap: 9, fontFamily: "var(--font-mono)", fontSize: 13, color: "#8a9298" }}>
            <Link to="/projects" style={{ color: "#8a9298", textDecoration: "none" }}>
              projects
            </Link>
            {isKeys ? (
              <>
                <span style={{ color: "#4d565b" }}>/</span>
                <span style={{ color: "#e8ebed" }}>keys</span>
              </>
            ) : null}
            {activeSlug ? (
              <>
                <span style={{ color: "#4d565b" }}>/</span>
                <span style={{ color: "#e8ebed" }}>{activeSlug}</span>
              </>
            ) : null}
          </div>
          <button
            type="button"
            data-testid="topbar-search"
            onClick={openSearchOverlay}
            style={{
              background: "var(--color-card)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "#8a9298",
              padding: "7px 13px",
              borderRadius: 8,
              fontSize: 13,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 9,
            }}
          >
            ⌕ Semantic search
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, border: "1px solid rgba(255,255,255,0.14)", borderRadius: 4, padding: "1px 5px" }}>
              ⌘K
            </span>
          </button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "30px 36px 60px" }}>
          <Outlet />
        </div>
      </main>

      <SearchOverlay />
    </div>
  );
}