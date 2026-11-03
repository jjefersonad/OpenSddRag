import type { ChangeSummary } from "../../api/changes";

export const CHANGES_PAGE_SIZE = 8;

const STAGE_RANK: Record<string, number> = {
  Apply: 0,
  Tasks: 1,
  Verify: 2,
  Design: 3,
  Spec: 4,
  Propose: 5,
  Sync: 6,
  Archive: 7,
};

/** Active lifecycle phase, or the last reached one when every phase is done. */
export function changeStage(summary: ChangeSummary): string {
  const active = summary.phases.find((phase) => phase.status === "active");
  return active?.name ?? summary.phases.at(-1)?.name ?? "—";
}

/** Compact UTC start date for the changes list (`23 Oct 2026`). */
export function formatChangeDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function changeStartAt(summary: ChangeSummary): string | null {
  return summary.started_at ?? summary.updated_at;
}

export function paginateChanges<T>(items: T[], page: number, pageSize = CHANGES_PAGE_SIZE): T[] {
  const safePage = Math.max(0, page);
  return items.slice(safePage * pageSize, safePage * pageSize + pageSize);
}

/** `web-change-reader` → `Web change reader` — a manager-readable label. */
export function humanizeChangeName(change: string): string {
  const words = change.replace(/[-_]+/g, " ").trim();
  if (!words) return change;
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function taskProgressLabel(progress: { done: number; total: number } | undefined): string {
  if (!progress || progress.total <= 0) return "—";
  return `${progress.done}/${progress.total}`;
}

export function taskProgressRatio(progress: { done: number; total: number } | undefined): number {
  if (!progress || progress.total <= 0) return 0;
  return Math.min(1, progress.done / progress.total);
}

export function stageColor(stage: string): string {
  if (stage === "Apply" || stage === "Tasks") return "#34d399";
  if (stage === "Verify" || stage === "Sync") return "#fbbf24";
  if (stage === "Design") return "#a78bfa";
  if (stage === "Propose" || stage === "Spec") return "#60a5fa";
  return "#8a9298";
}

/** Execution first, then most recently updated — what a PM scans first. */
export function sortChangesForManager(changes: ChangeSummary[]): ChangeSummary[] {
  return [...changes].sort((left, right) => {
    const rankDelta = (STAGE_RANK[changeStage(left)] ?? 50) - (STAGE_RANK[changeStage(right)] ?? 50);
    if (rankDelta !== 0) return rankDelta;
    return Date.parse(right.updated_at ?? "") - Date.parse(left.updated_at ?? "") || 0;
  });
}

export function portfolioLine(changes: ChangeSummary[]): string {
  const counts = new Map<string, number>();
  for (const summary of changes) {
    const stage = changeStage(summary);
    counts.set(stage, (counts.get(stage) ?? 0) + 1);
  }
  const parts = [`${changes.length} live`];
  for (const stage of ["Apply", "Tasks", "Verify", "Design", "Spec", "Propose", "Sync", "Archive"]) {
    const count = counts.get(stage);
    if (count) parts.push(`${count} ${stage}`);
  }
  return parts.join(" · ");
}
