/** Flow registry client (web-api delta REQ-008). */

import { apiRequest } from "./client";
import type { FlowInfo } from "./types";

export function listFlows(): Promise<FlowInfo[]> {
  return apiRequest<FlowInfo[]>("/flows");
}
