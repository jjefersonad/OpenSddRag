/** Domain types mirrored from the /api/v1 responses (AGENT_GUIDE §4). */

export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

/** `GET /api/v1/projects/:slug` — project plus per-type artifact counts. */
export interface ProjectDetailData extends Project {
  summary?: Record<string, number>;
}

/** An SDD artifact (proposal/spec/design/task/test). */
export interface Artifact {
  id: string;
  name: string;
  type: string;
  status: string;
  metadata?: Record<string, unknown>;
  content?: string;
  created_at?: string | null;
  updated_at?: string | null;
}

/** A harness rule (harness-rules-management). */
export interface HarnessRule {
  id: string;
  name: string;
  trigger: string;
  category: string;
  severity: string;
  instruction: string;
  enabled: boolean;
}

/** One semantic-search hit (web-api-management REQ-005). */
export interface SearchResult {
  type: string;
  title: string;
  snippet: string;
  project: string;
  score: number;
  slug?: string | null;
}
