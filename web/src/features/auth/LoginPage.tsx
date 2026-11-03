import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { setToken, verifyToken } from "../../api/client";

/** Login screen — paste the management token, validated before persisting
 *  (design D4). Invalid tokens are rejected without being stored. */
export default function LoginPage() {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const ok = await verifyToken(value.trim());
      if (ok) {
        setToken(value.trim());
        // D1 route model: `/` became the public landing; the dashboard lives
        // at `/projects`.
        navigate("/projects");
      } else {
        setError("Invalid token — check MANAGEMENT_API_TOKEN and try again.");
      }
    } catch {
      setError("Could not reach the API. Is the server running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100%",
        display: "grid",
        placeItems: "center",
        background: "var(--color-page)",
      }}
    >
      <form
        onSubmit={onSubmit}
        style={{
          background: "var(--color-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "12px",
          padding: "32px",
          width: "360px",
          display: "grid",
          gap: "12px",
        }}
      >
        <h1 style={{ margin: 0, fontSize: "20px" }}>OpenSddRag</h1>
        <label htmlFor="token" className="label">
          Management token
        </label>
        <input
          id="token"
          type="password"
          autoComplete="off"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          style={{
            background: "var(--color-inset)",
            border: "1px solid var(--color-border)",
            borderRadius: "8px",
            padding: "8px 10px",
            color: "var(--color-text-primary)",
            fontFamily: "var(--font-mono)",
          }}
        />
        <button
          type="submit"
          disabled={busy}
          style={{
            background: "var(--color-accent)",
            color: "var(--color-on-accent)",
            border: "none",
            borderRadius: "8px",
            padding: "10px",
            fontWeight: 600,
            cursor: busy ? "default" : "pointer",
          }}
        >
          {busy ? "Connecting…" : "Sign in"}
        </button>
        {error ? (
          <p role="alert" style={{ color: "var(--color-danger)", margin: 0 }}>
            {error}
          </p>
        ) : null}
      </form>
    </main>
  );
}
