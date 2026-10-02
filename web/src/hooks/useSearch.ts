import { useEffect, useRef, useState } from "react";
import { searchArtifacts } from "../api/search";
import type { SearchResult } from "../api/types";
import { useDebounced } from "./useDebounced";

export interface UseSearchResult {
  results: SearchResult[];
  loading: boolean;
  error: string | null;
}

const DEBOUNCE_MS = 200;

/** Semantic search with a 200ms debounce and AbortController cancellation of
 *  the previous in-flight request (web-dashboard-ui REQ-005, design D5). */
export function useSearch(query: string, limit = 5): UseSearchResult {
  const debouncedQuery = useDebounced(query.trim(), DEBOUNCE_MS);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!debouncedQuery) {
      setResults([]);
      setLoading(false);
      setError(null);
      return;
    }
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);
    searchArtifacts(debouncedQuery, limit, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setResults(data);
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "search failed");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [debouncedQuery, limit]);

  return { results, loading, error };
}
