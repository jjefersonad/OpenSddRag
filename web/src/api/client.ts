/** Central HTTP layer for the /api/v1 management API.
 *
 * - Injects `Authorization: Bearer <token>` from localStorage on every call.
 * - Normalizes error envelopes into `ApiError {code, message, details}`.
 * - On HTTP 401 clears the stored token and triggers the unauthorized handler
 *   (default: redirect to `/login`).  (design D3/D4/D8)
 */

export const API_BASE: string =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

const TOKEN_KEY = "opensddrag.management_token";

export class ApiError extends Error {
  readonly code: string;
  readonly details?: unknown;

  constructor(code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.details = details;
  }
}

// ── Token storage ────────────────────────────────────────────────────────────

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ── Unauthorized handler (redirect to /login) ────────────────────────────────

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler = () => {
  window.location.assign("/login");
};

/** Override the 401 side effect (tests inject a spy). */
export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  unauthorizedHandler = handler;
}

// ── Request core ─────────────────────────────────────────────────────────────

export interface RequestOptions {
  method?: string;
  body?: unknown;
  /** Explicit token override (used by login validation). */
  token?: string | null;
  /** When true, a 401 does NOT clear the token / redirect (login probe). */
  allowUnauthorized?: boolean;
  /** Abort signal (search overlay cancels superseded requests). */
  signal?: AbortSignal;
}

async function toApiError(response: Response): Promise<ApiError> {
  let code = `HTTP_${response.status}`;
  let message = `request failed with status ${response.status}`;
  let details: unknown;
  try {
    const body = (await response.json()) as {
      error?: { code?: string; message?: string; details?: unknown };
    };
    if (body?.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      details = body.error.details;
    }
  } catch {
    /* body was empty or not JSON — keep the fallback */
  }
  return new ApiError(code, message, details);
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const token = options.token !== undefined ? options.token : getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  if (response.status === 401) {
    if (!options.allowUnauthorized) {
      clearToken();
      unauthorizedHandler();
    }
    throw await toApiError(response);
  }

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as T;
}

/** Validate a candidate management token without side effects (design D4). */
export async function verifyToken(token: string): Promise<boolean> {
  try {
    await apiRequest("/projects", { token, allowUnauthorized: true });
    return true;
  } catch (error) {
    if (error instanceof ApiError && error.code === "UNAUTHORIZED") {
      return false;
    }
    throw error;
  }
}

// ── Optimistic mutation helper (design D8) ───────────────────────────────────

/**
 * Apply a local mutation immediately, run the async action, and roll back if
 * it fails. The error is re-thrown so the caller can surface it.
 */
export async function optimistic<T>(options: {
  apply: () => void;
  action: () => Promise<T>;
  rollback: () => void;
}): Promise<T> {
  options.apply();
  try {
    return await options.action();
  } catch (error) {
    options.rollback();
    throw error;
  }
}
