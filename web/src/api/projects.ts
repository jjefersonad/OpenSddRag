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

export function getProject(slug: string): Promise<ProjectDetailData> {
  return apiRequest<ProjectDetailData>(`/projects/${slug}`);
}
