/** Per-domain API client for artifacts (artifact-management REQ-001/002). */

import { apiRequest } from "./client";
import type { Artifact } from "./types";

export function listArtifacts(slug: string, type?: string): Promise<Artifact[]> {
  const query = type ? `?type=${encodeURIComponent(type)}` : "";
  return apiRequest<Artifact[]>(`/projects/${slug}/artifacts${query}`);
}

export function getArtifact(id: string): Promise<Artifact> {
  return apiRequest<Artifact>(`/artifacts/${id}`);
}
