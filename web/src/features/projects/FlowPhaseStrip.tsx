import type { FlowSummary } from "../../api/types";

/**
 * FlowPhaseStrip (REQ-014 multi-flow, design D6): renders a flow's declared
 * lifecycle phases as done/active/pending dots. Omitted entirely by the
 * caller when the flow's phase is null (no declared lifecycle) — graceful
 * degradation.
 */

const STATE_STYLE = {
  done: { dot: "var(--color-accent)", label: "#5b6469" },
  active: { dot: "#34d399", label: "var(--color-text)" },
  pending: { dot: "rgba(255,255,255,0.18)", label: "#5b6469" },
} as const;

type State = keyof typeof STATE_STYLE;

export default function FlowPhaseStrip({
  flow,
  summary,
  lifecycle,
}: {
  flow: string;
  summary: FlowSummary;
  lifecycle: { name: string; kinds: string[] }[];
}) {
  if (!lifecycle?.length) return null;

  let activeIndex = lifecycle.findIndex((p) => p.name === summary.phase);
  if (activeIndex === -1) activeIndex = -1; // phase null → everything pending except done

  const last = lifecycle.length - 1;
  return (
    <div
      data-testid={`phase-strip-${flow}`}
      style={{
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        background: "var(--color-inset)",
        border: "1px solid var(--color-border)",
        borderRadius: "12px",
        padding: "16px 14px",
        gap: 0,
      }}
    >
      {lifecycle
        .filter((p) => p.kinds.length > 0 || p.name === lifecycle[last].name)
        .map((phase, visibleIndex) => {
          // phases with kinds map to artifacts; the final Archive phase is done
          // only when the whole flow is done (phase === last name).
          let state: State = "pending";
          if (phase.kinds.length === 0) {
            state = summary.phase === lifecycle[last].name ? "active" : "pending";
          } else {
            const idx = lifecycle.indexOf(phase);
            if (summary.phase && idx < activeIndex) state = "done";
            else if (idx === activeIndex) state = "active";
          }
          const style = STATE_STYLE[state];
          return (
            <div key={phase.name} style={{ display: "flex", alignItems: "center" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, minWidth: 74 }}>
                <div style={{ width: 9, height: 9, borderRadius: 99, background: style.dot, boxShadow: state === "active" ? "0 0 10px rgba(52,211,153,0.5)" : undefined }} />
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: style.label, fontWeight: state === "active" ? 600 : 400 }}>
                  {phase.name}
                </span>
              </div>
              {visibleIndex < lifecycle.length - 1 && (
                <div style={{ width: 30, height: 1.5, background: "var(--color-border)", margin: "0 2px 20px" }} />
              )}
            </div>
          );
        })}
      {summary.task_progress.total > 0 ? (
        <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--color-text-tertiary)" }}>
          {summary.task_progress.done} / {summary.task_progress.total} tasks
        </span>
      ) : null}
    </div>
  );
}