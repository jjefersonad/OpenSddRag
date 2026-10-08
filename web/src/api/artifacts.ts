/** Per-domain API client for artifacts (artifact-management REQ-001/002 +
 *  web-api delta REQ-009: `flow` field + optional ?flow= filter). */

import { apiRequest } from "./client";
import type { Artifact } from "./types";

export function listArtifacts(slug: string, type?: string, flow?: string): Promise<Artifact[]> {
  const params = new URLSearchParams();
  if (type) params.set("type", type);
  if (flow) params.set("flow", flow);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiRequest<Artifact[]>(`/projects/${slug}/artifacts${query}`);
}

export function getArtifact(id: string): Promise<Artifact> {
  return apiRequest<Artifact>(`/artifacts/${id}`);
}