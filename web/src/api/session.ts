/** Working-context client (project detail, design D4). */

import { apiRequest } from "./client";

export interface SessionSummary {
  active_artifacts: { id: string; name: string; type: string }[];
  note?: string | null;
}

export function getSession(slug: string): Promise<SessionSummary> {
  return apiRequest<SessionSummary>(`/projects/${slug}/session`);
}
