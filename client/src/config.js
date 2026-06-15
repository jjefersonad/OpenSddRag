import { existsSync, readFileSync } from "fs";
import { join } from "path";

export const DEFAULT_SERVER_URL = "http://localhost:8000";

/**
 * Parse opensddrag.yaml from cwd.
 * Reads both `server:` and `server_url:` keys for backward compatibility.
 * Returns { project, server_url } or null on missing/malformed file.
 */
export function loadOpensddragYaml(cwd) {
  const yamlPath = join(cwd, "opensddrag.yaml");
  if (!existsSync(yamlPath)) return null;
  try {
    const text = readFileSync(yamlPath, "utf8");
    const projectMatch = text.match(/^project:\s*["']?(.+?)["']?\s*$/m);
    const serverMatch = text.match(/^(?:server_url|server):\s*["']?(.+?)["']?\s*$/m);
    return {
      project: projectMatch?.[1]?.trim() ?? null,
      server_url: serverMatch?.[1]?.trim() ?? null,
    };
  } catch {
    process.stderr.write("Warning: Ignoring malformed opensddrag.yaml\n");
    return null;
  }
}

/**
 * Resolve the MCP server URL with precedence:
 *   1. opts.server  (--server CLI flag)
 *   2. OPENSDDRAG_SERVER_URL env var
 *   3. opensddrag.yaml server_url / server field
 *   4. DEFAULT_SERVER_URL
 */
export function resolveServerUrl(opts, cwd) {
  if (opts?.server) return opts.server;
  if (process.env.OPENSDDRAG_SERVER_URL) return process.env.OPENSDDRAG_SERVER_URL;
  const yaml = loadOpensddragYaml(cwd ?? process.cwd());
  if (yaml?.server_url) return yaml.server_url;
  return DEFAULT_SERVER_URL;
}

/**
 * Resolve the API key with precedence:
 *   1. opts.apiKey  (--api-key CLI flag)
 *   2. OPENSDDRAG_API_KEY env var
 *   3. null
 */
export function resolveApiKey(opts) {
  if (opts?.apiKey) return opts.apiKey;
  if (process.env.OPENSDDRAG_API_KEY) return process.env.OPENSDDRAG_API_KEY;
  return null;
}
