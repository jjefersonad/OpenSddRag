/** Semantic search API (web-api-management REQ-005). */

import { apiRequest } from "./client";
import type { SearchResult } from "./types";

export function searchArtifacts(
  query: string,
  limit = 5,
  signal?: AbortSignal,
): Promise<SearchResult[]> {
  return apiRequest<SearchResult[]>(
    `/search?q=${encodeURIComponent(query)}&limit=${limit}`,
    { signal },
  );
}
