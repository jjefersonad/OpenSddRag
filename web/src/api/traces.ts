/** Per-domain API client for execution traces (web-api REQ-001). */

import { apiRequest } from "./client";
import type { ExecutionTrace } from "./types";

export function listTraces(slug: string, limit = 20): Promise<ExecutionTrace[]> {
  return apiRequest<ExecutionTrace[]>(`/projects/${slug}/traces?limit=${limit}`);
}
