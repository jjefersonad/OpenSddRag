/** Domain types mirrored from the /api/v1 responses (AGENT_GUIDE §4). */

export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  language?: string;
  /** Derived phase of the default flow (null when its flow has no lifecycle). */
  phase?: string | null;
  /** Aggregate task progress across live changes (project-management REQ-007). */
  task_progress?: { done: number; total: number };
  /** Most recently updated live change (null when none). */
  change?: string | null;
  /** Mini pipeline of that change: one entry per lifecycle phase. */
  phases?: { name: string; status: "done" | "active" | "pending" }[];
  created_at?: string | null;
  updated_at?: string | null;
}

/** `GET /api/v1/projects/:slug` — project plus per-type artifact counts. */
export interface ProjectDetailData extends Project {
  summary?: Record<string, number>;
  /** Active change name (enriched detail, project delta REQ-003). */
  change?: string | null;
  /** Per-flow summaries (design D8). */
  flows?: FlowSummary[];
}

/** An SDD artifact (proposal/spec/design/task/test). */
export interface Artifact {
  id: string;
  name: string;
  type: string;
  status: string;
  flow?: string;
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

/** One registered flow (web-api delta REQ-008). */
export interface FlowInfo {
  flow: string;
  kinds: { kind: string; rules: Record<string, unknown> }[];
  lifecycle: { name: string; kinds: string[] }[] | null;
  harness_triggers?: string[];
  registered_at?: string | null;
}

/** Per-flow summary of an enriched project detail (design D8). */
export interface FlowSummary {
  flow: string;
  phase: string | null;
  task_progress: { done: number; total: number };
}

/** One execution trace (episodic memory). */
export interface ExecutionTrace {
  id: string;
  action: string;
  query?: string | null;
  result_summary?: string | null;
  created_at?: string | null;
}
