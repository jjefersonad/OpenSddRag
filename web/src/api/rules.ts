/** Harness rules API (harness-rules-management REQ-001/003). */

import { apiRequest } from "./client";
import type { HarnessRule } from "./types";

export function listRules(slug: string, enabledAll = false): Promise<HarnessRule[]> {
  const query = enabledAll ? "?enabled_all=true" : "";
  return apiRequest<HarnessRule[]>(`/projects/${slug}/rules${query}`);
}

export function setRuleEnabled(
  slug: string,
  ruleId: string,
  enabled: boolean,
): Promise<HarnessRule> {
  return apiRequest<HarnessRule>(`/projects/${slug}/rules/${ruleId}`, {
    method: "PATCH",
    body: { enabled },
  });
}
