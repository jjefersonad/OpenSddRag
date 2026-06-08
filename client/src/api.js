import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const CLIENT_INFO = { name: "opensddrag-cli", version: "0.1.0" };

async function withMcp(serverUrl, fn, apiKey) {
  const client = new Client(CLIENT_INFO);
  const transportOpts = apiKey
    ? { requestInit: { headers: { Authorization: `Bearer ${apiKey}` } } }
    : {};
  const transport = new StreamableHTTPClientTransport(
    new URL(`${serverUrl.replace(/\/+$/, "")}/mcp`),
    transportOpts,
  );
  await client.connect(transport);
  try {
    return await fn(client);
  } finally {
    await client.close();
  }
}

function parseToolResult(result) {
  const text = result.content?.[0]?.text ?? "";
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(text || "Unexpected response from server");
  }
}

export async function checkHealth(serverUrl, apiKey) {
  await withMcp(serverUrl, async () => {}, apiKey);
}

export async function createProject(serverUrl, { slug, name, description }, apiKey) {
  return withMcp(serverUrl, async (client) => {
    const args = { slug, name };
    if (description) args.description = description;
    const result = await client.callTool({ name: "create_project", arguments: args });
    return parseToolResult(result);
  }, apiKey);
}

export async function listProjects(serverUrl, apiKey) {
  return withMcp(serverUrl, async (client) => {
    const result = await client.callTool({ name: "list_projects", arguments: {} });
    return parseToolResult(result);
  }, apiKey);
}
