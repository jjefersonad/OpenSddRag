import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { listKeys, revokeKey, type ApiKeyRecord, type CreatedApiKey } from "../../api/keys";
import { listProjects } from "../../api/projects";
import type { Project } from "../../api/types";
import ConfirmDialog from "../../components/ConfirmDialog";
import CreateKeyModal from "./CreateKeyModal";

const TH = {
  fontFamily: "var(--font-mono)",
  fontSize: 10,
  letterSpacing: "0.08em",
  textTransform: "uppercase" as const,
  color: "#5b6469",
  textAlign: "left" as const,
  fontWeight: 500,
  padding: "8px 12px",
  borderBottom: "1px solid var(--color-border)",
};

const TD = {
  padding: "11px 12px",
  borderBottom: "1px solid rgba(255,255,255,0.06)",
  fontSize: 13,
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const date = iso.slice(0, 10);
  return date;
}

function statusColor(status: ApiKeyRecord["status"]): string {
  if (status === "active") return "#34d399";
  if (status === "expired") return "#fbbf24";
  return "#9aa2a8";
}

/** MCP API key management: list, create (plaintext once), revoke. */
export default function KeysPage() {
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [filter, setFilter] = useState("all");
  const [includeRevoked, setIncludeRevoked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<CreatedApiKey | null>(null);
  const [copied, setCopied] = useState(false);
  const [revoking, setRevoking] = useState<ApiKeyRecord | null>(null);
  const [revokeBusy, setRevokeBusy] = useState(false);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  function query() {
    if (filter === "global") return { scope: "global" as const, includeRevoked };
    if (filter !== "all") return { project: filter, includeRevoked };
    return { includeRevoked };
  }

  function reload() {
    setLoading(true);
    setError(null);
    return listKeys(query())
      .then(setKeys)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "failed to load keys");
        setKeys([]);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    listProjects().then(setProjects, () => setProjects([]));
  }, []);

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload when filters change
  }, [filter, includeRevoked]);

  async function copyKey() {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.key);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  async function confirmRevoke() {
    if (!revoking) return;
    setRevokeBusy(true);
    setRevokeError(null);
    try {
      await revokeKey(revoking.id);
      setRevoking(null);
      await reload();
    } catch (err) {
      setRevokeError(err instanceof ApiError ? err.message : "Could not revoke the key.");
    } finally {
      setRevokeBusy(false);
    }
  }

  return (
    <div data-testid="keys-page">
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 22 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>API keys</h1>
          <p style={{ margin: "8px 0 0", color: "#8a9298", fontSize: 13, maxWidth: 560 }}>
            MCP Bearer keys for Cursor and Claude. The plaintext is shown once at creation.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setCreating(true)}
          style={{
            background: "var(--color-accent)",
            color: "var(--color-on-accent)",
            border: "none",
            borderRadius: 8,
            padding: "8px 14px",
            fontWeight: 600,
          }}
        >
          New key
        </button>
      </div>

      {created ? (
        <div
          data-testid="key-reveal"
          style={{
            background: "var(--color-card)",
            border: "1px solid var(--color-border)",
            borderRadius: 12,
            padding: 16,
            marginBottom: 18,
          }}
        >
          <p style={{ margin: "0 0 8px", fontWeight: 600 }}>Save this key — it will not be shown again.</p>
          <code
            data-testid="created-key"
            style={{
              display: "block",
              fontFamily: "var(--font-mono)",
              fontSize: 13,
              wordBreak: "break-all",
              color: "#34d399",
              marginBottom: 10,
            }}
          >
            {created.key}
          </code>
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" onClick={() => void copyKey()}>
              {copied ? "Copied" : "Copy"}
            </button>
            <button type="button" onClick={() => setCreated(null)}>
              Done
            </button>
          </div>
        </div>
      ) : null}

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
        <label htmlFor="key-filter" className="label" style={{ margin: 0 }}>
          Filter
        </label>
        <select id="key-filter" value={filter} onChange={(event) => setFilter(event.target.value)}>
          <option value="all">All</option>
          <option value="global">Global</option>
          {projects.map((project) => (
            <option key={project.slug} value={project.slug}>
              {project.slug}
            </option>
          ))}
        </select>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#8a9298" }}>
          <input
            type="checkbox"
            checked={includeRevoked}
            onChange={(event) => setIncludeRevoked(event.target.checked)}
          />
          Show revoked
        </label>
      </div>

      {loading ? <p>Loading…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {!loading && !error && keys.length === 0 ? <p>No API keys.</p> : null}

      {!loading && keys.length > 0 ? (
        <table data-testid="keys-table" style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={TH}>Description</th>
              <th style={TH}>Prefix</th>
              <th style={TH}>Scope</th>
              <th style={TH}>Created</th>
              <th style={TH}>Expires</th>
              <th style={TH}>Status</th>
              <th style={TH} />
            </tr>
          </thead>
          <tbody>
            {keys.map((key) => (
              <tr key={key.id} data-testid={`key-row-${key.prefix}`}>
                <td style={TD}>{key.description || "—"}</td>
                <td style={{ ...TD, fontFamily: "var(--font-mono)" }}>{key.prefix}</td>
                <td style={{ ...TD, fontFamily: "var(--font-mono)" }}>{key.project_slug ?? "global"}</td>
                <td style={TD}>{formatDate(key.created_at)}</td>
                <td style={TD}>{formatDate(key.expires_at)}</td>
                <td style={{ ...TD, color: statusColor(key.status), fontFamily: "var(--font-mono)", fontSize: 12 }}>
                  {key.status}
                </td>
                <td style={TD}>
                  {key.status === "active" ? (
                    <button
                      type="button"
                      onClick={() => {
                        setRevokeError(null);
                        setRevoking(key);
                      }}
                      style={{
                        background: "transparent",
                        border: "1px solid var(--color-border)",
                        borderRadius: 6,
                        color: "var(--color-danger)",
                        fontSize: 12,
                        padding: "4px 8px",
                        cursor: "pointer",
                      }}
                    >
                      Revoke
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}

      {creating ? (
        <CreateKeyModal
          projects={projects}
          onClose={() => setCreating(false)}
          onCreated={(item) => {
            setCreating(false);
            setCopied(false);
            setCreated(item);
            void reload();
          }}
        />
      ) : null}

      {revoking ? (
        <ConfirmDialog
          title="Revoke API key"
          message={`Revoke ${revoking.prefix}…? Connected MCP clients using this key will get 401.`}
          confirmLabel="Revoke"
          busy={revokeBusy}
          error={revokeError}
          onConfirm={() => void confirmRevoke()}
          onClose={() => setRevoking(null)}
        />
      ) : null}
    </div>
  );
}
