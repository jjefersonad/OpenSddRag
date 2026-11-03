/** Changes-in-progress client (web-overview-changes-pipeline REQ-011)
 *  plus the per-change document bundle (web-change-reader REQ-014). */

import { apiRequest } from "./client";
import type { Artifact } from "./types";

export interface ChangePhase {
  name: string;
  status: "done" | "active" | "pending";
  desc: string;
}

export interface ChangeSummary {
  change: string;
  flow: string;
  started_at?: string | null;
  updated_at: string | null;
  task_progress: { done: number; total: number };
  phases: ChangePhase[];
}

export interface ChangeTask {
  id?: string;
  name: string;
  status: string;
  content: string;
  done: boolean;
}

export interface ChangeBundle {
  change: string;
  flow: string;
  proposal: Artifact | null;
  design: Artifact | null;
  specs: Artifact[];
  tasks: ChangeTask[];
  task_count: number;
}

/** Page size requested from the API. The server slices; the client does not. */
export const CHANGES_PAGE_SIZE = 8;

export interface ChangesPage {
  items: ChangeSummary[];
  total: number;
  page: number;
  page_size: number;
}

export function getChanges(slug: string, page = 1, pageSize = CHANGES_PAGE_SIZE): Promise<ChangesPage> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return apiRequest<ChangesPage>(`/projects/${slug}/changes?${params}`);
}

export function getChangeBundle(slug: string, change: string): Promise<ChangeBundle> {
  return apiRequest<ChangeBundle>(
    `/projects/${slug}/changes/${encodeURIComponent(change)}`,
  );
}