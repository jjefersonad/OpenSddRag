import { useState } from "react";
import type { Artifact } from "../../api/types";
import MarkdownBody from "../../components/MarkdownBody";
import { parseRequirements } from "./parsers";
import SpecRequirementsBody from "./SpecRequirementsBody";

const STATUS_COLOR: Record<string, string> = {
  draft: "var(--color-warn)",
  active: "var(--color-info)",
  archived: "var(--color-text-tertiary)",
};

/** Full spec card (REQ-015): collapsed header with chevron, mono spec name,
 *  parsed requirement count and status chip; expanded body renders the parsed
 *  requirements — falling back to the raw content when nothing parses (the
 *  "No parsed requirements" placeholder must never render). */
export default function SpecCard({ artifact, title }: { artifact: Artifact; title?: string }) {
  const [expanded, setExpanded] = useState(false);
  const reqCount = parseRequirements(artifact.content ?? "").length;
  const heading = title ?? artifact.name;

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
        <span style={{ display: "flex", alignItems: "baseline", gap: "8px", minWidth: 0 }}>
          <span aria-hidden="true">{expanded ? "▾" : "▸"}</span>
          <span style={{ fontFamily: title ? "inherit" : "var(--font-mono)" }}>{heading}</span>
          <span style={{ color: "var(--color-text-secondary)", fontSize: "12px" }}>
            {reqCount} requirements
          </span>
        </span>
        <span
          className="label"
          style={{ color: STATUS_COLOR[artifact.status] ?? "var(--color-text-secondary)" }}
        >
          {artifact.status}
        </span>
      </button>
      {expanded ? (
        reqCount > 0 ? (
          <div style={{ padding: "0 14px 14px" }}>
            <SpecRequirementsBody artifact={artifact} />
          </div>
        ) : (
          <div style={{ padding: "0 14px 14px" }}>
            <MarkdownBody>{artifact.content ?? ""}</MarkdownBody>
          </div>
        )
      ) : null}
    </article>
  );
}