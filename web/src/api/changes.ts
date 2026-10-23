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

export function getChanges(slug: string): Promise<ChangeSummary[]> {
  return apiRequest<ChangeSummary[]>(`/projects/${slug}/changes`);
}

export function getChangeBundle(slug: string, change: string): Promise<ChangeBundle> {
  return apiRequest<ChangeBundle>(
    `/projects/${slug}/changes/${encodeURIComponent(change)}`,
  );
}