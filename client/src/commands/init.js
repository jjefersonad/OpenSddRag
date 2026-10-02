import { Command } from "commander";
import { input, confirm, checkbox, password } from "@inquirer/prompts";
import chalk from "chalk";
import { existsSync, readFileSync, writeFileSync } from "fs";
import { join, basename } from "path";

import { checkHealth, createProject, addRule, registerFlow } from "../api.js";
import { DEFAULT_RULES } from "../harness-rules.js";
import { DEFAULT_SERVER_URL, resolveServerUrl, resolveApiKey } from "../config.js";
import {
  resolveSelectedFlows,
  installFlows,
  registerManifests,
  toServerManifest,
  ManifestError,
  DEFAULT_FLOWS_ROOT,
} from "../flows.js";

// ── Config writers ─────────────────────────────────────────────────────────────

function writeClaudeCode(cwd, serverUrl, apiKey) {
  const mcpPath = join(cwd, ".mcp.json");
  let config = {};
  if (existsSync(mcpPath)) {
    try { config = JSON.parse(readFileSync(mcpPath, "utf8")); } catch {}
  }
  config.mcpServers = config.mcpServers || {};
  const entry = { type: "http", url: `${serverUrl}/mcp` };
  if (apiKey) {
    entry.headers = { Authorization: `Bearer ${apiKey}` };
  }
  config.mcpServers.opensddrag = entry;
  writeFileSync(mcpPath, JSON.stringify(config, null, 2) + "\n");
  return ".mcp.json";
}

function writeOpenCode(cwd, serverUrl, _apiKey) {
  const configPath = join(cwd, "opencode.json");
  let config = {};
  if (existsSync(configPath)) {
    try { config = JSON.parse(readFileSync(configPath, "utf8")); } catch {}
  }
  config.mcp = config.mcp || {};
  config.mcp.opensddrag = {
    type: "remote",
    url: `${serverUrl}/mcp`,
    enabled: true,
  };
  if (_apiKey) {
    config.mcp.opensddrag.headers = { Authorization: `Bearer ${_apiKey}` };
  }
  writeFileSync(configPath, JSON.stringify(config, null, 2) + "\n");
  return "opencode.json";
}

const TOOL_WRITERS = {
  "Claude Code": writeClaudeCode,
  "OpenCode":    writeOpenCode,
};

// ── Command ────────────────────────────────────────────────────────────────────

export const initCommand = new Command("init")
  .description("Connect the current project to an OpenSddRag MCP server")
  .option("--project <slug>", "Project slug (default: current directory name)")
  .option("--name <name>", "Project display name")
  .option("--server <url>", "OpenSddRag server URL")
  .option("--api-key <key>", "API key for authenticated servers")
  .option("--tools <list>", "Comma-separated tools to configure: claude,opencode (default: ask)")
  .option("--flow <slugs>", "Comma-separated flows to install (default: sdd)")
  .option("--yes", "Skip confirmation prompts")
  .action(async (opts) => {
    const cwd = process.cwd();

    console.log(chalk.bold("\n  OpenSddRag — Project Init\n"));

    // ── Inputs ────────────────────────────────────────────────────────────────
    const resolvedUrl = resolveServerUrl(opts, cwd);
    let serverUrl;
    if (opts.yes || resolvedUrl !== DEFAULT_SERVER_URL) {
      serverUrl = resolvedUrl;
    } else {
      serverUrl = await input({ message: "OpenSddRag server URL:", default: DEFAULT_SERVER_URL });
    }

    let apiKey = resolveApiKey(opts);
    if (!apiKey && !opts.yes) {
      apiKey = await password({
        message: "API key (leave blank to skip — server must have AUTH_ENABLED=false):",
        mask: "*",
      }) || null;
    }

    const slug = opts.project ||
      await input({
        message: "Project slug:",
        default: basename(cwd).toLowerCase().replace(/[^a-z0-9-]/g, "-"),
      });

    const name = opts.name ||
      await input({
        message: "Project display name:",
        default: slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      });

    // ── Which tools to configure ──────────────────────────────────────────────
    let selectedTools;
    if (opts.tools) {
      const map = { claude: "Claude Code", opencode: "OpenCode" };
      selectedTools = opts.tools.split(",").map((t) => map[t.trim().toLowerCase()]).filter(Boolean);
    } else {
      selectedTools = await checkbox({
        message: "Which AI tools to configure?",
        choices: [
          { name: "Claude Code  (.claude/settings.json)", value: "Claude Code", checked: true },
          { name: "OpenCode     (opencode.json)",          value: "OpenCode",    checked: false },
        ],
      });
    }

    if (selectedTools.length === 0) {
      console.log(chalk.yellow("\n  No tools selected. Exiting.\n"));
      process.exit(0);
    }

    // ── Which flows to install ────────────────────────────────────────────────
    // Resolve and VALIDATE flows before any file is written: a malformed
    // manifest aborts with a diagnostic naming the missing field and a
    // non-zero exit (client-cli REQ-011). `--yes` defaults to sdd alone;
    // otherwise an interactive multi-select is offered (sdd pre-selected).
    let selectedManifests;
    try {
      selectedManifests = await resolveSelectedFlows({
        flowArg: opts.flow,
        yes: opts.yes,
        flowsRoot: DEFAULT_FLOWS_ROOT,
      });
    } catch (err) {
      if (err instanceof ManifestError) {
        console.error(chalk.red(`\n  ✗ ${err.message}`));
        process.exit(1);
      }
      throw err;
    }
    if (selectedManifests.length === 0) {
      console.log(chalk.yellow("\n  No flows selected. Exiting.\n"));
      process.exit(0);
    }
    const flowNames = selectedManifests.map((m) => m.flow);

    // ── Preview ───────────────────────────────────────────────────────────────
    console.log("\n" + chalk.dim("  Will create/update:"));
    if (selectedTools.includes("Claude Code")) {
      console.log(chalk.dim("    .mcp.json                                    — MCP server (type: http)"));
      console.log(chalk.dim("    .claude/skills/opensddrag-*/SKILL.md         — individual skill per command"));
      console.log(chalk.dim("    .agents/skills/opensddrag-*/SKILL.md         — individual skill per command"));
      console.log(chalk.dim("    .claude/commands/opsr/       — slash commands (/opsr:propose, /opsr:apply, /opsr:harness...)"));
    }
    if (selectedTools.includes("OpenCode")) {
      console.log(chalk.dim("    opencode.json                — MCP server"));
      console.log(chalk.dim("    .opencode/skills/opensddrag-*/SKILL.md     — OpenCode-native skills"));
      console.log(chalk.dim("    .opencode/commands/opsr/     — slash commands (/opsr:propose, /opsr:apply...)"));
    }
    console.log(chalk.dim(`    Flows: ${flowNames.join(", ")}`));
    console.log(chalk.dim("    CLAUDE.md                    — OpenSddRag section(s)"));
    console.log(chalk.dim(`    Remote: register '${slug}' in central database\n`));

    if (!opts.yes) {
      const ok = await confirm({ message: "Proceed?", default: true });
      if (!ok) process.exit(0);
    }

    // ── 1. Server health ──────────────────────────────────────────────────────
    process.stdout.write(chalk.bold("  1/4 ") + "Connecting to server... ");
    try {
      await checkHealth(serverUrl, apiKey);
      console.log(chalk.green("✓"));
    } catch {
      console.log(chalk.red("✗"));
      const isLocal = serverUrl.includes("localhost") || serverUrl.includes("127.0.0.1");
      console.error(chalk.red(`\n  Cannot reach ${serverUrl}`));
      if (isLocal) {
        console.error(chalk.dim("  Make sure the OpenSddRag server is running:"));
        console.error(chalk.dim("    docker compose up -d"));
      }
      console.error(chalk.dim("  Pass --server <url> or set OPENSDDRAG_SERVER_URL."));
      process.exit(1);
    }

    // ── 2. Register project ───────────────────────────────────────────────────
    process.stdout.write(chalk.bold("  2/4 ") + "Registering project in database... ");
    let project;
    try {
      project = await createProject(serverUrl, { slug, name }, apiKey);
      console.log(project.already_existed
        ? chalk.yellow("✓ (already existed)")
        : chalk.green(`✓ (id: ${project.id})`));
    } catch (err) {
      console.log(chalk.red("✗"));
      console.error(chalk.red(`\n  ${err.message}`));
      process.exit(1);
    }

    // ── 2b. Seed default harness rules (idempotent upsert by name) ───────────
    for (const rule of DEFAULT_RULES) {
      try {
        await addRule(serverUrl, slug, rule, apiKey);
      } catch (err) {
        console.error(chalk.yellow(`\n  Warning: could not seed rule '${rule.name}': ${err.message}`));
      }
    }

    // ── 2c. Register non-sdd flow manifests with the server (best effort) ────
    const reg = await registerManifests({
      manifests: selectedManifests,
      registerFn: (m) => registerFlow(serverUrl, toServerManifest(m), apiKey),
    });
    if (reg.registered.length) {
      console.log(chalk.dim(`    Registered flows: ${reg.registered.join(", ")}`));
    }
    if (reg.skipped.length) {
      console.log(chalk.yellow(`    Skipped flow registration: ${reg.skipped.join(", ")}`));
    }

    // ── 3. Configure AI tools ─────────────────────────────────────────────────
    process.stdout.write(chalk.bold("  3/4 ") + "Configuring AI tools... ");
    const configured = [];
    for (const tool of selectedTools) {
      const file = TOOL_WRITERS[tool](cwd, serverUrl, apiKey);
      configured.push(`${tool} → ${file}`);
    }
    console.log(chalk.green("✓"));
    for (const c of configured) console.log(chalk.dim(`    ${c}`));

    // ── 3b. Install selected flows (skills, commands, CLAUDE.md section) ──────
    process.stdout.write(chalk.bold("  4/4 ") + "Installing flows... ");
    const installSummary = await installFlows({
      cwd,
      flowsRoot: DEFAULT_FLOWS_ROOT,
      manifests: selectedManifests,
      slug,
      serverUrl,
      tools: selectedTools,
      projectName: name,
    });
    console.log(chalk.green(`✓ (${installSummary.skills} skills, ${installSummary.commands} commands)`));
    for (const act of installSummary.claudeMdActions) {
      if (act.flow === "sdd" && act.action === "already") {
        console.log(chalk.dim("    ✓ (already has OpenSddRag section)"));
      } else {
        console.log(chalk.dim(`    flow → ${act.flow} (${act.action})`));
      }
    }

    // opensddrag.yaml (local project marker) — always refreshed
    writeFileSync(join(cwd, "opensddrag.yaml"), `project: ${slug}\nserver: ${serverUrl}\n`);

    // ── Done ──────────────────────────────────────────────────────────────────
    console.log(chalk.bold.green("\n  ✓ Project connected to OpenSddRag!\n"));
    console.log("  Open the project in your AI tool — the MCP server is configured.\n");
  });
