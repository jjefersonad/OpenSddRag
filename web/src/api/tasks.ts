/** Task artifacts API (web-api-management REQ-004). */

import { apiRequest } from "./client";
import type { Artifact } from "./types";

export function setTaskDone(
  slug: string,
  taskId: string,
  done: boolean,
): Promise<Artifact> {
  return apiRequest<Artifact>(`/projects/${slug}/tasks/${taskId}`, {
    method: "PATCH",
    body: { done },
  });
}
