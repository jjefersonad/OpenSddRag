/** Per-domain API client for artifacts (artifact-management REQ-001/002 +
 *  web-api delta REQ-009: `flow` field + optional ?flow= filter). */

import { apiRequest } from "./client";
import type { Artifact } from "./types";

export function listArtifacts(
  slug: string,
  type?: string,
  flow?: string,
  includeContent?: boolean,
): Promise<Artifact[]> {
  const params = new URLSearchParams();
  if (type) params.set("type", type);
  if (flow) params.set("flow", flow);
  if (includeContent) params.set("include", "content");
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiRequest<Artifact[]>(`/projects/${slug}/artifacts${query}`);
}

export function getArtifact(id: string): Promise<Artifact> {
  return apiRequest<Artifact>(`/artifacts/${id}`);
}

export interface ArtifactWriteInput {
  name: string;
  content: string;
  status?: string;
  metadata?: Record<string, unknown>;
}

export function createArtifact(
  slug: string,
  input: ArtifactWriteInput & { type: string },
): Promise<Artifact> {
  return apiRequest<Artifact>(`/projects/${encodeURIComponent(slug)}/artifacts`, {
    method: "POST",
    body: input,
  });
}

export function updateArtifact(id: string, input: ArtifactWriteInput): Promise<Artifact> {
  return apiRequest<Artifact>(`/artifacts/${id}`, { method: "PATCH", body: input });
}

export function deleteArtifact(id: string): Promise<{ deleted: boolean; id: string }> {
  return apiRequest(`/artifacts/${id}`, { method: "DELETE" });
}