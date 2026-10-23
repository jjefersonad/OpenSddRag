import { useEffect, useState } from "react";
import { listArtifacts } from "../api/artifacts";
import type { Artifact } from "../api/types";

export interface UseArtifactsResult {
  artifacts: Artifact[];
  loading: boolean;
  error: string | null;
}

/** Fetches a project's artifacts (optionally filtered by type) once per
 *  (slug, type) pair (artifact-management REQ-001). */
export function useArtifacts(
  slug: string | undefined,
  type?: string,
  flow?: string,
  includeContent?: boolean,
): UseArtifactsResult {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (!slug) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    listArtifacts(slug, type, flow, includeContent)
      .then((data) => {
        if (active) setArtifacts(data);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "failed to load artifacts");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [slug, type, flow, includeContent]);

  return { artifacts, loading, error };
}
