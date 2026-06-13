import { Command } from "commander";
import { input, confirm, checkbox, password } from "@inquirer/prompts";
import chalk from "chalk";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { join, basename } from "path";

import { checkHealth, createProject } from "../api.js";
import { renderClaudeMdBlock, renderClaudeMdStandalone } from "../templates/claude-md.js";
import { getCommands } from "../templates/commands/index.js";
import { getOpenCodeCommands } from "../templates/commands/opencode.js";
import { getSkills } from "../templates/skills/index.js";
import { getHarnessSkill } from "../templates/skill-md.js";

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
  .option("--server <url>", "OpenSddRag server URL", "http://localhost:8000")
  .option("--api-key <key>", "API key for authenticated servers")
  .option("--tools <list>", "Comma-separated tools to configure: claude,opencode (default: ask)")
  .option("--yes", "Skip confirmation prompts")
  .action(async (opts) => {
    const cwd = process.cwd();

    console.log(chalk.bold("\n  OpenSddRag — Project Init\n"));

    // ── Inputs ────────────────────────────────────────────────────────────────
    const serverUrl = opts.server ||
      await input({ message: "OpenSddRag server URL:", default: "http://localhost:8000" });

    // Prompt for API key when connecting to a remote server
    const isRemote = !serverUrl.includes("localhost") && !serverUrl.includes("127.0.0.1");
    let apiKey = opts.apiKey || null;
    if (!apiKey && isRemote && !opts.yes) {
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
    console.log(chalk.dim("    CLAUDE.md                    — OpenSddRag section"));
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
      console.error(chalk.red(`\n  Cannot reach ${serverUrl}`));
      console.error(chalk.dim("  Make sure the OpenSddRag server is running:"));
      console.error(chalk.dim("    docker compose up -d"));
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

    // ── 3. Configure AI tools ─────────────────────────────────────────────────
    process.stdout.write(chalk.bold("  3/4 ") + "Configuring AI tools... ");
    const configured = [];
    for (const tool of selectedTools) {
      const file = TOOL_WRITERS[tool](cwd, serverUrl, apiKey);
      configured.push(`${tool} → ${file}`);
    }
    // Individual skill files per command — roots determined by selected tools
    const skills = [
      ...getSkills(slug, serverUrl),
      // Harness management skill — installed alongside the SDD skills so
      // both Claude Code and OpenCode can manage project rules via the
      // `add_rule` / `list_rules` / `get_harness_checklist` MCP tools.
      {
        name: "opensddrag-harness",
        content: getHarnessSkill({ slug, serverUrl }),
      },
    ];
    const skillRoots = [];
    if (selectedTools.includes("Claude Code")) {
      skillRoots.push(join(cwd, ".claude", "skills"));
      skillRoots.push(join(cwd, ".agents", "skills"));
    }
    if (selectedTools.includes("OpenCode")) {
      skillRoots.push(join(cwd, ".opencode", "skills"));
    }
    for (const skill of skills) {
      for (const root of skillRoots) {
        const skillDir = join(root, skill.name);
        mkdirSync(skillDir, { recursive: true });
        writeFileSync(join(skillDir, "SKILL.md"), skill.content);
      }
      if (skillRoots.length > 0) {
        configured.push(`skill → ${skill.name}/SKILL.md (${skillRoots.length} root(s))`);
      }
    }
    console.log(chalk.green("✓"));
    for (const c of configured) console.log(chalk.dim(`    ${c}`));

    // ── 4. Slash commands ────────────────────────────────────────────────────
    process.stdout.write(chalk.bold("  4/5 ") + "Writing slash commands... ");
    let totalCommands = 0;
    if (selectedTools.includes("Claude Code")) {
      const commands = getCommands(slug, serverUrl);
      for (const cmd of commands) {
        const cmdDir = join(cwd, ".claude", "commands", cmd.folder);
        mkdirSync(cmdDir, { recursive: true });
        writeFileSync(join(cmdDir, `${cmd.name}.md`), cmd.content);
      }
      totalCommands += commands.length;
    }
    if (selectedTools.includes("OpenCode")) {
      const opencodeCommands = getOpenCodeCommands(slug, serverUrl);
      for (const cmd of opencodeCommands) {
        const cmdDir = join(cwd, ".opencode", "commands", cmd.folder);
        mkdirSync(cmdDir, { recursive: true });
        writeFileSync(join(cmdDir, `${cmd.name}.md`), cmd.content);
      }
      totalCommands += opencodeCommands.length;
    }
    console.log(chalk.green(`✓ (${totalCommands} commands)`));

    // ── 5. CLAUDE.md ──────────────────────────────────────────────────────────
    process.stdout.write(chalk.bold("  5/5 ") + "Updating CLAUDE.md... ");
    const claudeMdPath = join(cwd, "CLAUDE.md");
    if (existsSync(claudeMdPath)) {
      const content = readFileSync(claudeMdPath, "utf8");
      if (content.includes("OpenSddRag")) {
        console.log(chalk.yellow("✓ (already has OpenSddRag section)"));
      } else {
        writeFileSync(claudeMdPath, content.trimEnd() + "\n" + renderClaudeMdBlock({ slug, serverUrl }) + "\n");
        console.log(chalk.green("✓ (appended)"));
      }
    } else {
      writeFileSync(claudeMdPath, renderClaudeMdStandalone({ projectName: name, slug, serverUrl }));
      console.log(chalk.green("✓ (created)"));
    }

    // opensddrag.yaml (local project marker)
    if (!existsSync(join(cwd, "opensddrag.yaml"))) {
      writeFileSync(join(cwd, "opensddrag.yaml"), `project: ${slug}\nserver: ${serverUrl}\n`);
    }

    // ── Done ──────────────────────────────────────────────────────────────────
    console.log(chalk.bold.green("\n  ✓ Project connected to OpenSddRag!\n"));
    console.log("  Open the project in your AI tool — the MCP server is configured.\n");
  });
