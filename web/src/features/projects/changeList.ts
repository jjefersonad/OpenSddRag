import type { ChangeSummary } from "../../api/changes";

export const CHANGES_PAGE_SIZE = 8;

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
