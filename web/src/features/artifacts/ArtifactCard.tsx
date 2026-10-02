import type { Artifact } from "../../api/types";

/** Compact card for non-spec artifacts (proposal/design/task). */
export default function ArtifactCard({ artifact }: { artifact: Artifact }) {
  return (
    <article
      style={{
        background: "var(--color-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "12px",
        padding: "12px 14px",
        marginBottom: "10px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span style={{ fontFamily: "var(--font-mono)" }}>{artifact.name}</span>
        <span className="label" style={{ color: "var(--color-text-secondary)" }}>
          {artifact.status}
        </span>
      </div>
      {artifact.content ? (
        <pre
          style={{
            margin: "8px 0 0",
            whiteSpace: "pre-wrap",
            color: "var(--color-text-secondary)",
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
          }}
        >
          {artifact.content}
        </pre>
      ) : null}
    </article>
  );
}
