/** Per-domain API client for projects (project-management REQ-001/002/003). */

import { apiRequest } from "./client";
import type { Project, ProjectDetailData } from "./types";

export interface CreateProjectInput {
  name: string;
  slug: string;
  description?: string;
}

export function listProjects(): Promise<Project[]> {
  return apiRequest<Project[]>("/projects");
}

export function createProject(input: CreateProjectInput): Promise<Project> {
  return apiRequest<Project>("/projects", { method: "POST", body: input });
}

export interface UpdateProjectInput {
  name?: string;
  slug?: string;
  description?: string;
  language?: string;
}

export function updateProject(slug: string, input: UpdateProjectInput): Promise<Project> {
  return apiRequest<Project>(`/projects/${encodeURIComponent(slug)}`, { method: "PATCH", body: input });
}

export function deleteProject(slug: string): Promise<{ deleted: boolean; slug: string }> {
  return apiRequest(`/projects/${encodeURIComponent(slug)}`, { method: "DELETE" });
}

export function getProject(slug: string): Promise<ProjectDetailData> {
  return apiRequest<ProjectDetailData>(`/projects/${slug}`);
}
