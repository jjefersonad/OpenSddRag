import { useEffect, useState } from "react";
import { listRules } from "../api/rules";
import type { HarnessRule } from "../api/types";

export interface UseRulesResult {
  rules: HarnessRule[];
  loading: boolean;
  error: string | null;
}

/** Lists a project's enabled harness rules (harness-rules-management REQ-001). */
export function useRules(slug: string | undefined): UseRulesResult {
  const [rules, setRules] = useState<HarnessRule[]>([]);
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
    listRules(slug)
      .then((data) => {
        if (active) setRules(data);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "failed to load rules");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [slug]);

  return { rules, loading, error };
}
