import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSearch } from "../../hooks/useSearch";

/** ⌘K / Ctrl+K semantic-search overlay (web-dashboard-ui REQ-005, design D5).
 *  Esc or backdrop click closes; selecting a hit navigates to its project. */
export default function SearchOverlay() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { results, loading, error } = useSearch(open ? query : "");

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      } else if (event.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  if (!open) return null;

  function select(project: string) {
    navigate(`/p/${project}`);
    setOpen(false);
    setQuery("");
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Semantic search"
      onClick={() => setOpen(false)}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "grid",
        placeItems: "start center",
        paddingTop: "12vh",
      }}
    >
      <div
        onClick={(event) => event.stopPropagation()}
        style={{
          width: "min(640px, 92vw)",
          background: "var(--color-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "12px",
          padding: "16px",
        }}
      >
        <input
          role="searchbox"
          aria-label="Search"
          autoFocus
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          style={{
            width: "100%",
            background: "var(--color-inset)",
            border: "1px solid var(--color-border)",
            borderRadius: "8px",
            padding: "10px",
            color: "var(--color-text-primary)",
          }}
        />
        {loading ? <p style={{ color: "var(--color-text-secondary)" }}>Searching…</p> : null}
        {error ? <p role="alert">{error}</p> : null}
        <ul style={{ listStyle: "none", padding: 0, margin: "12px 0 0" }}>
          {results.map((result, index) => (
            <li key={`${result.type}-${result.slug ?? result.title}-${index}`}>
              <button
                type="button"
                onClick={() => select(result.project)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  background: "transparent",
                  border: "none",
                  borderBottom: "1px solid var(--color-border)",
                  padding: "10px 4px",
                  cursor: "pointer",
                  color: "var(--color-text-primary)",
                }}
              >
                <span className="label" style={{ color: "var(--color-accent)" }}>
                  {result.type}
                </span>{" "}
                <span style={{ fontFamily: "var(--font-mono)" }}>{result.title}</span>
                <div style={{ color: "var(--color-text-secondary)", fontSize: "12px" }}>
                  {result.snippet}
                </div>
                <div className="label" style={{ color: "var(--color-text-tertiary)" }}>
                  {result.project} · {result.score}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
