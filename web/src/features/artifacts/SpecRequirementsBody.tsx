import { useState } from "react";
import type { Artifact } from "../../api/types";
import { parseRequirements } from "./parsers";

/**
 * Structured spec body (REQ-015): one block per `### Requirement:` — mono id,
 * title, SHALL text — with collapsible WHEN/THEN scenario pairs (WHEN in
 * amber, THEN in primary text). Data-testids `scenario-when` / `scenario-then`
 * are the structural hooks (AGENT_GUIDE §5). Callers own the empty-content
 * fallback: this component renders nothing for zero parsed requirements.
 */
export default function SpecRequirementsBody({ artifact }: { artifact: Artifact }) {
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

  if (reqs.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {reqs.map((req, index) => (
        <article
          key={`${req.id}-${index}`}
          style={{ border: "1px solid var(--color-border)", borderRadius: "12px", padding: "14px" }}
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
                    <p data-testid="scenario-when" style={{ margin: "0", fontSize: "13px", color: "var(--color-warn)" }}>
                      WHEN {scenario.when}
                    </p>
                    <p data-testid="scenario-then" style={{ margin: "4px 0 0", fontSize: "13px", color: "var(--color-text-primary)" }}>
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