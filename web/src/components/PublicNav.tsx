import { Link } from "react-router-dom";

/**
 * Public top navigation (design D2, REQ-012): logo, GitHub, Docs and the
 * launch/sign-in action — rendered on landing, docs and login screens when
 * the user is not authenticated.
 */
export default function PublicNav() {
  return (
    <header
      data-testid="public-nav"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "16px",
        padding: "16px 24px",
        borderBottom: "1px solid var(--color-border)",
        background: "var(--color-sidebar)",
      }}
    >
      <Link to="/" style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)", fontWeight: 600 }}>
        OpenSddRag
      </Link>
      <a href="https://github.com" target="_blank" rel="noreferrer" style={{ color: "var(--color-text-secondary)" }}>
        GitHub
      </a>
      <Link to="/docs" style={{ color: "var(--color-text-secondary)" }}>
        Docs
      </Link>
      <Link
        to="/login"
        style={{ marginLeft: "auto", color: "var(--color-accent)" }}
      >
        Launch app →
      </Link>
    </header>
  );
}