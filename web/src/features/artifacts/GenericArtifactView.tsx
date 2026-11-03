import type { Artifact } from "../../api/types";
import MarkdownBody from "../../components/MarkdownBody";
import { hasStructuredRenderer } from "./parsers";

/**
 * Generic artifact renderer (REQ-015, design D7): metadata + raw content —
 * the fallback for kinds without a structured renderer (any non-SDD flow's
 * kind works on day one).
 */
export default function GenericArtifactView({ artifact }: { artifact: Artifact }) {
  return (
    <article
      data-testid={`generic-artifact-${artifact.name}`}
      style={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: "12px", padding: "14px" }}
    >
      <header style={{ display: "flex", gap: "10px", alignItems: "baseline", marginBottom: "10px" }}>
        <strong style={{ fontFamily: "var(--font-mono)" }}>{artifact.name}</strong>
        <span className="label">{artifact.type}</span>
        {artifact.flow ? <span className="label">{artifact.flow}</span> : null}
        <span className="label">{artifact.status}</span>
      </header>
      <ul style={{ margin: "0 0 10px", paddingLeft: "18px", color: "var(--color-text-tertiary)", fontSize: "12px" }}>
        {Object.entries(artifact.metadata ?? {}).map(([key, value]) => (
          <li key={key}>
            {key}: {String(value)}
          </li>
        ))}
      </ul>
      <MarkdownBody>{artifact.content ?? ""}</MarkdownBody>
    </article>
  );
}

export { hasStructuredRenderer };