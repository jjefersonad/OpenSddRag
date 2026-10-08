/** Change-tree client (web-artifact-hierarchy, web-api delta REQ-010). */

import { apiRequest } from "./client";

export interface TreeNode {
  id: string;
  name: string;
  type: string;
  status: string;
  depth: number;
  flow: string;
}

export interface TreeEdge {
  source: string;
  target: string;
  relationship_type: string;
}

export interface TreeData {
  change: string | null;
  flows: { flow: string; nodes: TreeNode[]; edges: TreeEdge[] }[];
}

export function getTree(slug: string): Promise<TreeData> {
  return apiRequest<TreeData>(`/projects/${slug}/tree`);
}