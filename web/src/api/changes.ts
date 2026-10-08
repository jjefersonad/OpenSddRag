/** Changes-in-progress client (web-overview-changes-pipeline REQ-011). */

import { apiRequest } from "./client";

export interface ChangePhase {
  name: string;
  status: "done" | "active" | "pending";
  desc: string;
}

export interface ChangeSummary {
  change: string;
  flow: string;
  updated_at: string | null;
  task_progress: { done: number; total: number };
  phases: ChangePhase[];
}

export function getChanges(slug: string): Promise<ChangeSummary[]> {
  return apiRequest<ChangeSummary[]>(`/projects/${slug}/changes`);
}