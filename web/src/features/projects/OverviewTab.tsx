import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { type ChangeSummary } from "../../api/changes";
import { getSession, type SessionSummary } from "../../api/session";
import { listTraces } from "../../api/traces";
import type { ExecutionTrace } from "../../api/types";
import {
  changeStage,
  changeStartAt,
  formatChangeDate,
  humanizeChangeName,
  stageColor,
  taskProgressLabel,
  taskProgressRatio,
} from "./changeList";

/**
 * Overview tab (REQ-014 two-column overview): left column is a paginated
 * list of live changes (name, start date, stage). Clicking a row opens the
 * Change Reader. The right column stacks Working context and Execution trace.
 * The live changes list is fetched once by the detail shell and passed down.
 */

/** Mono uppercase section label shared by the pipeline column heading. */
const SECTION_LABEL = {
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  letterSpacing: "0.09em",
  textTransform: "uppercase",
  color: "#5b6469",
  marginBottom: 14,
} as const;

/** Card look shared by the right-column side panels. */
const CARD_STYLE = {
  background: "var(--color-card)",
  border: "1px solid var(--color-border)",
  borderRadius: 12,
  padding: 16,
} as const;

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

function ChangeList({
  slug,
  changes,
  total,
  page,
  pageSize,
  onPage,
}: {
  slug: string;
  changes: ChangeSummary[];
  total: number;
  page: number;
  pageSize: number;
  onPage: (page: number) => void;
}) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, pageCount);

  return (
    <div data-testid="changes-list">
      <p data-testid="changes-portfolio" style={{ margin: "0 0 12px", fontFamily: "var(--font-mono)", fontSize: 11, color: "#8a9298" }}>
        {total} live
      </p>
      <table style={{ width: "100%", borderCollapse: "collapse", background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 12, overflow: "hidden" }}>
        <thead>
          <tr>
            <th style={TH}>Change</th>
            <th style={{ ...TH, width: 88 }}>Progress</th>
            <th style={{ ...TH, width: 118 }}>Started</th>
            <th style={{ ...TH, width: 96 }}>Stage</th>
          </tr>
        </thead>
        <tbody>
          {changes.map((summary) => {
            const stage = changeStage(summary);
            const ratio = taskProgressRatio(summary.task_progress);
            return (
            <tr key={summary.change}>
              <td style={TD} colSpan={4}>
                <Link
                  to={`/p/${slug}/c/${encodeURIComponent(summary.change)}`}
                  data-testid={`change-card-${summary.change}`}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 88px 118px 96px",
                    alignItems: "center",
                    margin: "-11px -12px",
                    padding: "11px 12px",
                    textDecoration: "none",
                    color: "inherit",
                  }}
                >
                  <span style={{ minWidth: 0 }}>
                    <span style={{ display: "block", fontSize: 13.5, fontWeight: 600, color: "#e8ebed", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {humanizeChangeName(summary.change)}
                    </span>
                    <span style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: 11, color: "#5b6469", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {summary.change}
                    </span>
                  </span>
                  <span data-testid={`change-progress-${summary.change}`} style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#cdd3d7" }}>
                    <span>{taskProgressLabel(summary.task_progress)}</span>
                    <span style={{ display: "block", height: 3, marginTop: 5, background: "rgba(255,255,255,0.08)", borderRadius: 99, overflow: "hidden" }}>
                      <span style={{ display: "block", height: "100%", width: `${Math.round(ratio * 100)}%`, background: "#34d399" }} />
                    </span>
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#8a9298" }}>
                    {formatChangeDate(changeStartAt(summary))}
                  </span>
                  <span
                    data-testid={`change-stage-${summary.change}`}
                    style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: stageColor(stage) }}
                  >
                    {stage}
                  </span>
                </Link>
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
      {total > pageSize ? (
        <div
          data-testid="changes-pagination"
          style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 10, marginTop: 12 }}
        >
          <button
            type="button"
            disabled={safePage <= 1}
            onClick={() => onPage(safePage - 1)}
            style={{
              background: "transparent",
              border: "1px solid var(--color-border)",
              color: safePage <= 1 ? "#4d565b" : "#cdd3d7",
              borderRadius: 6,
              padding: "4px 10px",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              cursor: safePage <= 1 ? "default" : "pointer",
            }}
          >
            Previous
          </button>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#8a9298" }}>
            {safePage} / {pageCount}
          </span>
          <button
            type="button"
            disabled={safePage >= pageCount}
            onClick={() => onPage(safePage + 1)}
            style={{
              background: "transparent",
              border: "1px solid var(--color-border)",
              color: safePage >= pageCount ? "#4d565b" : "#cdd3d7",
              borderRadius: 6,
              padding: "4px 10px",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              cursor: safePage >= pageCount ? "default" : "pointer",
            }}
          >
            Next
          </button>
        </div>
      ) : null}
    </div>
  );
}

function WorkingContextPanel({ session }: { session: SessionSummary | null }) {
  return (
    <div data-testid="working-context-panel" style={CARD_STYLE}>
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
  );
}

function TracesPanel({ traces }: { traces: ExecutionTrace[] }) {
  return (
    <div data-testid="traces-panel" style={CARD_STYLE}>
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
  );
}

export default function OverviewTab({
  slug,
  changes,
  total,
  page,
  pageSize,
  onPage,
}: {
  slug: string;
  changes: ChangeSummary[] | null;
  total: number;
  page: number;
  pageSize: number;
  onPage: (page: number) => void;
}) {
  const [session, setSession] = useState<SessionSummary | null>(null);
  const [traces, setTraces] = useState<ExecutionTrace[]>([]);

  useEffect(() => {
    let alive = true;
    getSession(slug).then((s) => alive && setSession(s), () => alive && setSession(null));
    listTraces(slug).then((t) => alive && setTraces(t), () => alive && setTraces([]));
    return () => {
      alive = false;
    };
  }, [slug]);

  return (
    <div className="overview-grid">
      <div>
        <div style={SECTION_LABEL}>Live changes</div>
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
          <ChangeList slug={slug} changes={changes} total={total} page={page} pageSize={pageSize} onPage={onPage} />
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <WorkingContextPanel session={session} />
        <TracesPanel traces={traces} />
      </div>
    </div>
  );
}
