import type { ChangePhase } from "../../api/changes";

/**
 * FlowPhaseStrip (REQ-014, design D7): the prototype's horizontal compact
 * phase strip — 13px done/active/pending dots, 30px connectors (green up to
 * the active phase) and mono labels — rendered from the active change's
 * server-derived phases. Omitted entirely by the caller when the change's
 * flow declares no lifecycle (or the phases list is empty).
 */

const DOT_COLOR = {
  done: "var(--color-accent)",
  active: "var(--color-accent-hover)",
  pending: "#2b3238",
} as const;

type Status = keyof typeof DOT_COLOR;

export default function FlowPhaseStrip({
  flow,
  phases,
  selected = null,
  onSelect,
}: {
  flow: string;
  phases: Pick<ChangePhase, "name" | "status">[];
  /** Phase whose items are on screen. Only used when `onSelect` is set. */
  selected?: string | null;
  /** Makes each phase a toggle. A second click on the selected phase clears it. */
  onSelect?: (name: string) => void;
}) {
  if (phases.length === 0) return null;

  return (
    <div
      data-testid={`phase-strip-${flow}`}
      style={{
        display: "flex",
        alignItems: "center",
        background: "var(--color-inset)",
        border: "1px solid var(--color-border)",
        borderRadius: "11px",
        padding: "14px 16px",
        marginBottom: "22px",
        overflowX: "auto",
      }}
    >
      {phases.map((phase, i) => {
        const status = phase.status as Status;
        const isSelected = selected === phase.name;
        const mark = <PhaseMark name={phase.name} status={status} selected={isSelected} />;
        return (
          <div key={phase.name} style={{ display: "flex", alignItems: "center" }}>
            {onSelect ? (
              <button
                type="button"
                data-testid={`strip-phase-${flow}-${phase.name}`}
                data-state={status}
                data-selected={isSelected ? "true" : "false"}
                aria-pressed={isSelected}
                onClick={() => onSelect(phase.name)}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 7,
                  minWidth: 74,
                  padding: "4px 2px",
                  background: isSelected ? "rgba(16,185,129,0.1)" : "transparent",
                  border: "none",
                  borderRadius: 8,
                  cursor: "pointer",
                  color: "inherit",
                  font: "inherit",
                }}
              >
                {mark}
              </button>
            ) : (
              <div
                data-testid={`strip-phase-${flow}-${phase.name}`}
                data-state={status}
                style={{ display: "flex" }}
              >
                {mark}
              </div>
            )}
            {i < phases.length - 1 ? (
              <div style={{ width: 30, height: 1.5, margin: "0 1px 18px", background: status === "done" ? "#10b981" : "rgba(255,255,255,0.1)" }} />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function PhaseMark({
  name,
  status,
  selected,
}: {
  name: string;
  status: Status;
  selected: boolean;
}) {
  const dot = DOT_COLOR[status];
  return (
    <span style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 7, minWidth: 74 }}>
      <span
        style={{
          width: 13,
          height: 13,
          borderRadius: 99,
          background: dot,
          boxShadow: selected || status === "active" ? "0 0 0 4px rgba(52,211,153,0.18)" : undefined,
        }}
      />
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "11.5px",
          color: selected ? "var(--color-accent-hover)" : status === "pending" ? "var(--color-text-tertiary)" : "#cdd3d7",
          fontWeight: selected || status === "active" ? 600 : 500,
        }}
      >
        {name}
      </span>
    </span>
  );
}