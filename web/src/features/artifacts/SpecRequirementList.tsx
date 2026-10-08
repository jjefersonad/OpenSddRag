import { useState } from "react";
import type { Artifact } from "../../api/types";
import { parseRequirements } from "./parsers";

/** Structured spec renderer (REQ-015): SHALL requirement text with
 *  expandable WHEN/THEN scenario blocks (AGENT_GUIDE §5 expandedSpecs). */
export default function SpecRequirementList({ artifact }: { artifact: Artifact }) {
  const [open, setOpen] = useState<Set<number>>(new Set());

  const reqs = parseRequirements(artifact.content ?? "");

  function toggle(index: number) {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }

  if (reqs.length === 0) {
    return <p style={{ color: "var(--color-text-tertiary)" }}>No parsed requirements — raw content below.</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {reqs.map((req, index) => (
        <article
          key={`${req.id}-${index}`}
          style={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: "12px", padding: "14px" }}
        >
          <header style={{ display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "8px" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-accent)" }}>{req.id}</span>
            <strong style={{ fontSize: "14px" }}>{req.title}</strong>
          </header>
          <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "13.5px" }}>{req.shall}</p>
          {req.scenarios.map((scenario, sIndex) => {
            const isOpen = open.has(index * 100 + sIndex);
            return (
              <div key={`${scenario.name}-${sIndex}`}>
                <button
                  type="button"
                  aria-expanded={isOpen}
                  onClick={() => toggle(index * 100 + sIndex)}
                  style={{ marginTop: "8px" }}
                >
                  {scenario.name}
                </button>
                {isOpen ? (
                  <div style={{ paddingTop: "8px" }}>
                    <p data-testid="scenario-when" style={{ margin: "0", fontSize: "13px", color: "var(--color-text-secondary)" }}>
                      WHEN {scenario.when}
                    </p>
                    <p data-testid="scenario-then" style={{ margin: "4px 0 0", fontSize: "13px", color: "var(--color-text-secondary)" }}>
                      THEN {scenario.then}
                    </p>
                  </div>
                ) : null}
              </div>
            );
          })}
        </article>
      ))}
    </div>
  );
}