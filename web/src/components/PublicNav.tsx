import { Link } from "react-router-dom";

const linkStyle = {
  color: "var(--color-text-secondary)",
  textDecoration: "none",
  fontSize: "14px",
} as const;

/**
 * Public top navigation (design D2/D11, REQ-012/REQ-018): brand block (glyph
 * square, mono wordmark, version chip), GitHub, Docs and a filled accent
 * launch button — rendered on landing, docs and login screens when the user
 * is not authenticated. Content sits in a centered 1180px container.
 */
export default function PublicNav() {
  return (
    <header
      data-testid="public-nav"
      style={{ borderBottom: "1px solid var(--color-border)", background: "var(--color-page)" }}
    >
      <div
        data-testid="nav-inner"
        style={{
          maxWidth: "1180px",
          margin: "0 auto",
          padding: "22px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Link
          to="/"
          style={{ display: "flex", alignItems: "center", gap: "11px", textDecoration: "none", color: "inherit" }}
        >
          <span
            data-testid="nav-brand-mark"
            style={{
              width: "30px",
              height: "30px",
              borderRadius: "7px",
              background: "var(--color-accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "var(--font-mono)",
              fontWeight: 600,
              color: "var(--color-on-accent)",
              fontSize: "15px",
            }}
          >
            ⌘
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, fontSize: "15px", letterSpacing: "-0.01em" }}>
            OpenSddRag
          </span>
          <span
            data-testid="nav-version"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--color-text-tertiary)",
              border: "1px solid rgba(255,255,255,0.1)",
              padding: "2px 7px",
              borderRadius: "5px",
            }}
          >
            v{__APP_VERSION__}
          </span>
        </Link>
        <nav style={{ display: "flex", alignItems: "center", gap: "22px" }}>
          <a href="https://github.com" target="_blank" rel="noreferrer" style={linkStyle}>
            GitHub
          </a>
          <Link to="/docs" style={linkStyle}>
            Docs
          </Link>
          <Link
            to="/login"
            data-testid="nav-launch"
            style={{
              background: "var(--color-accent)",
              color: "var(--color-on-accent)",
              textDecoration: "none",
              fontWeight: 600,
              fontSize: "14px",
              padding: "9px 18px",
              borderRadius: "8px",
            }}
          >
            Launch app →
          </Link>
        </nav>
      </div>
    </header>
  );
}
