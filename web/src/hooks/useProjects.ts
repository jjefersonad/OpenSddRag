import { useCallback, useEffect, useState } from "react";
import { listProjects } from "../api/projects";
import type { Project } from "../api/types";

export interface UseProjectsResult {
  projects: Project[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** Dashboard data hook — a single fetch on mount (REQ-004), reloadable. */
export function useProjects(): UseProjectsResult {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    listProjects()
      .then((data) => {
        if (active) setProjects(data);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "failed to load projects");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [nonce]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);

  return { projects, loading, error, reload };
}
