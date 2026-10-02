import { useState } from "react";
import type { Artifact } from "../../api/types";

const STATUS_COLOR: Record<string, string> = {
  draft: "var(--color-warn)",
  active: "var(--color-info)",
  archived: "var(--color-text-tertiary)",
};

/** Expandable spec card — the AGENT_GUIDE §5 `expandedSpecs` behaviour. */
export default function SpecCard({ artifact }: { artifact: Artifact }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <article
      style={{
        background: "var(--color-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "12px",
        marginBottom: "10px",
        overflow: "hidden",
      }}
    >
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
        style={{
          width: "100%",
          textAlign: "left",
          background: "transparent",
          border: "none",
          color: "var(--color-text-primary)",
          padding: "12px 14px",
          cursor: "pointer",
          display: "flex",
          justifyContent: "space-between",
          gap: "8px",
        }}
      >
        <span style={{ fontFamily: "var(--font-mono)" }}>{artifact.name}</span>
        <span
          className="label"
          style={{ color: STATUS_COLOR[artifact.status] ?? "var(--color-text-secondary)" }}
        >
          {artifact.status}
        </span>
      </button>
      {expanded ? (
        <pre
          style={{
            margin: 0,
            padding: "0 14px 14px",
            whiteSpace: "pre-wrap",
            color: "var(--color-text-secondary)",
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
          }}
        >
          {artifact.content ?? ""}
        </pre>
      ) : null}
    </article>
  );
}
