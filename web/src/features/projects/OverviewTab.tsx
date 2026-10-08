import { useEffect, useState } from "react";
import { getChanges, type ChangePhase, type ChangeSummary } from "../../api/changes";
import { getSession } from "../../api/session";
import { listTraces } from "../../api/traces";
import type { ExecutionTrace } from "../../api/types";

/**
 * Overview tab (REQ-014 delta, web-overview-changes-pipeline): "Changes in
 * progress" — one card per live change with the per-change vertical phase
 * timeline (prototype's SDD pipeline grammar: 13px dots — done #10b981,
 * active #34d399 + glow, pending #2b3238 — 2px connectors, mono labels,
 * statusLabels, descs), then Working context and Execution trace.
 */

const DOT_COLOR = {
  done: "#10b981",
  active: "#34d399",
  pending: "#2b3238",
} as const;

const STATUS_TEXT: Record<string, string> = {
  done: "done",
  active: "in progress",
  pending: "pending",
};

function PhaseTimeline({ change, phases }: { change: string; phases: ChangePhase[] }) {
  return (
    <div style={{ position: "relative", paddingLeft: 8, marginTop: 12 }}>
      {phases.map((phase, i) => {
        const dot = DOT_COLOR[phase.status];
        const titleColor = phase.status === "pending" ? "#6b747a" : "#e8ebed";
        return (
          <div
            key={phase.name}
            data-testid={`phase-${change}-${phase.name}`}
            style={{ display: "flex", gap: 15, paddingBottom: 18, position: "relative" }}
          >
            <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div
                style={{
                  width: 15,
                  height: 15,
                  borderRadius: 99,
                  background: dot,
                  border: "2px solid #0a0c0d",
                  zIndex: 2,
                  boxShadow: phase.status === "active" ? "0 0 0 4px rgba(52,211,153,0.18)" : undefined,
                }}
              />
              {i < phases.length - 1 ? (
                <div style={{ flex: 1, width: 2, background: phase.status === "done" ? "#10b981" : "rgba(255,255,255,0.1)", marginTop: 2 }} />
              ) : null}
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: titleColor }}>{phase.name}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: dot }}>{STATUS_TEXT[phase.status] ?? phase.status}</span>
              </div>
              <div style={{ fontSize: 12.5, color: "#7a838a", marginTop: 2 }}>{phase.desc}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ChangeCard({ summary }: { summary: ChangeSummary }) {
  const { done, total } = summary.task_progress;
  return (
    <div
      data-testid={`change-card-${summary.change}`}
      style={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 18, marginBottom: 16 }}
    >
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 14.5, fontWeight: 600, color: "#e8ebed" }}>{summary.change}</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#34d399", background: "rgba(52,211,153,0.12)", borderRadius: 5, padding: "3px 8px" }}>
            {summary.flow}
          </span>
        </div>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 11.5, color: "#8a9298" }}>
          {done}/{total} tasks
        </span>
      </div>
      {summary.phases.length > 0 ? <PhaseTimeline change={summary.change} phases={summary.phases} /> : null}
    </div>
  );
}

export default function OverviewTab({ slug }: { slug: string }) {
  const [changes, setChanges] = useState<ChangeSummary[] | null>(null);
  const [session, setSession] = useState<{ active_artifacts: { id: string; name: string; type: string }[]; note?: string | null } | null>(null);
  const [traces, setTraces] = useState<ExecutionTrace[]>([]);

  useEffect(() => {
    let alive = true;
    getChanges(slug).then((c) => alive && setChanges(c), () => alive && setChanges([]));
    getSession(slug).then((s) => alive && setSession(s), () => alive && setSession(null));
    listTraces(slug).then((t) => alive && setTraces(t), () => alive && setTraces([]));
    return () => {
      alive = false;
    };
  }, [slug]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.09em", textTransform: "uppercase", color: "#5b6469", marginBottom: 14 }}>
          Changes in progress
        </div>
        {changes === null ? (
          <p style={{ color: "var(--color-text-tertiary)" }}>Loading…</p>
        ) : changes.length === 0 ? (
          <div
            data-testid="changes-empty"
            style={{ textAlign: "center", padding: 40, color: "#6b747a", fontSize: 13.5, border: "1px dashed rgba(255,255,255,0.1)", borderRadius: 12 }}
          >
            No active change — run <span style={{ fontFamily: "var(--font-mono)", color: "#34d399" }}>/opsr:propose</span> to start one.
          </div>
        ) : (
          changes.map((summary) => <ChangeCard key={summary.change} summary={summary} />)
        )}
      </div>

      <div
        data-testid="working-context-panel"
        style={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 16 }}
      >
        <div className="label" style={{ marginBottom: 10 }}>
          Working context
        </div>
        {session?.active_artifacts?.length ? (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
            {session.active_artifacts.map((a) => (
              <li key={a.id} style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
                {a.type} · {a.name}
              </li>
            ))}
          </ul>
        ) : (
          <p style={{ margin: 0, color: "var(--color-text-tertiary)", fontSize: 13 }}>No active artifacts.</p>
        )}
        {session?.note ? <p style={{ marginTop: 8, color: "var(--color-text-secondary)", fontSize: 13 }}>{session.note}</p> : null}
      </div>

      <div
        data-testid="traces-panel"
        style={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 16 }}
      >
        <div className="label" style={{ marginBottom: 10 }}>
          Execution trace
        </div>
        {traces.length === 0 ? (
          <p style={{ margin: 0, color: "var(--color-text-tertiary)", fontSize: 13 }}>No traces yet.</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
            {traces.map((t) => (
              <li key={t.id} style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
                <strong style={{ color: "var(--color-accent)" }}>{t.action}</strong> — {t.result_summary ?? ""}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}