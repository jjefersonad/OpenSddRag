import { apiRequest } from "./client";

export type ApiKeyStatus = "active" | "revoked" | "expired";

export interface ApiKeyRecord {
  id: string;
  prefix: string;
  description: string;
  project_slug: string | null;
  created_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  status: ApiKeyStatus;
}

export interface CreatedApiKey extends ApiKeyRecord {
  key: string;
}

export function listKeys(opts?: {
  project?: string;
  scope?: "global";
  includeRevoked?: boolean;
}): Promise<ApiKeyRecord[]> {
  const params = new URLSearchParams();
  if (opts?.project) params.set("project", opts.project);
  if (opts?.scope) params.set("scope", opts.scope);
  if (opts?.includeRevoked) params.set("include_revoked", "true");
  const query = params.toString();
  return apiRequest<ApiKeyRecord[]>(`/keys${query ? `?${query}` : ""}`);
}

export function createKey(body: {
  description?: string;
  project_slug?: string | null;
  expires_at?: string | null;
}): Promise<CreatedApiKey> {
  return apiRequest<CreatedApiKey>("/keys", { method: "POST", body });
}

export function revokeKey(id: string): Promise<ApiKeyRecord> {
  return apiRequest<ApiKeyRecord>(`/keys/${id}/revoke`, { method: "POST" });
}
