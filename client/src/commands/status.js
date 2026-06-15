import { Command } from "commander";
import chalk from "chalk";
import { existsSync, readFileSync } from "fs";
import { join } from "path";

import { checkHealth, listProjects } from "../api.js";
import { resolveServerUrl, loadOpensddragYaml } from "../config.js";

export const statusCommand = new Command("status")
  .description("Check OpenSddRag connection status for the current project")
  .option("--server <url>", "OpenSddRag server URL")
  .action(async (opts) => {
    const cwd = process.cwd();

    console.log(chalk.bold("\n  OpenSddRag — Status\n"));

    const serverUrl = resolveServerUrl(opts, cwd);
    const yaml = loadOpensddragYaml(cwd);
    const slug = yaml?.project ?? null;

    // ── Local config ──────────────────────────────────────────────────────────
    if (yaml) {
      console.log(chalk.green("  ✓") + ` opensddrag.yaml  →  project: ${chalk.cyan(slug)}`);
    } else {
      console.log(chalk.red("  ✗") + " opensddrag.yaml not found — run: " + chalk.dim("opensddrag init"));
    }

    // ── Skills ────────────────────────────────────────────────────────────────
    console.log(chalk.dim("\n  Skills (.claude/skills/ and .agents/skills/):"));
    const expectedSkills = ["opensddrag-propose","opensddrag-spec","opensddrag-design","opensddrag-tasks","opensddrag-apply","opensddrag-verify","opensddrag-sync","opensddrag-archive","opensddrag-explore","opensddrag-continue","opensddrag-status","opensddrag-flow","opensddrag-search"];
    const missingSkills = expectedSkills.filter((s) => !existsSync(join(cwd, ".claude", "skills", s, "SKILL.md")));
    if (missingSkills.length === 0) {
      console.log(chalk.green("    ✓") + " all " + expectedSkills.length + " skills present");
    } else {
      const present = expectedSkills.length - missingSkills.length;
      console.log(chalk.yellow(`    ! ${present}/${expectedSkills.length} skills present — missing: `) + missingSkills.join(", "));
    }

    // ── Claude Code ───────────────────────────────────────────────────────────
    console.log(chalk.dim("\n  Claude Code:"));
    const mcpJsonPath = join(cwd, ".mcp.json");
    if (existsSync(mcpJsonPath)) {
      try {
        const cfg = JSON.parse(readFileSync(mcpJsonPath, "utf8"));
        const mcp = cfg?.mcpServers?.opensddrag;
        if (mcp) {
          console.log(chalk.green("    ✓") + " .mcp.json  →  type: " + chalk.cyan(mcp.type) + "  url: " + chalk.cyan(mcp.url));
        } else {
          console.log(chalk.yellow("    !") + " .mcp.json exists but 'opensddrag' not configured");
        }
      } catch {
        console.log(chalk.red("    ✗") + " .mcp.json — invalid JSON");
      }
    } else {
      console.log(chalk.dim("    –") + " .mcp.json not found");
    }


    // ── Slash commands ────────────────────────────────────────────────────────
    console.log(chalk.dim("\n  Slash commands (.claude/commands/opsr/):"));
    const expectedCommands = ["propose", "spec", "design", "tasks", "apply", "verify", "sync", "archive", "explore", "continue", "status", "flow", "search"];
    const opsrDir = join(cwd, ".claude", "commands", "opsr");
    const missingCmds = expectedCommands.filter((c) => !existsSync(join(opsrDir, `${c}.md`)));
    if (missingCmds.length === 0) {
      console.log(chalk.green("    ✓") + " all commands present: " + chalk.dim(expectedCommands.map((c) => `/opsr:${c}`).join(", ")));
    } else {
      const present = expectedCommands.filter((c) => existsSync(join(opsrDir, `${c}.md`)));
      if (present.length > 0) console.log(chalk.green("    ✓") + " " + present.map((c) => `/opsr:${c}`).join(", "));
      console.log(chalk.yellow("    !") + " missing: " + missingCmds.map((c) => `/opsr:${c}`).join(", "));
    }

    // ── OpenCode ──────────────────────────────────────────────────────────────
    console.log(chalk.dim("\n  OpenCode:"));
    const opencodePath = join(cwd, "opencode.json");
    if (existsSync(opencodePath)) {
      try {
        const cfg = JSON.parse(readFileSync(opencodePath, "utf8"));
        const mcp = cfg?.mcp?.opensddrag;
        if (mcp) {
          console.log(chalk.green("    ✓") + " opencode.json  →  " + chalk.cyan(mcp.url));
        } else {
          console.log(chalk.yellow("    !") + " opencode.json exists but 'opensddrag' not configured");
        }
      } catch {
        console.log(chalk.red("    ✗") + " opencode.json — invalid JSON");
      }
    } else {
      console.log(chalk.dim("    –") + " opencode.json not found");
    }

    // ── CLAUDE.md ─────────────────────────────────────────────────────────────
    const claudeMd = join(cwd, "CLAUDE.md");
    console.log(chalk.dim("\n  CLAUDE.md:"));
    if (existsSync(claudeMd)) {
      const content = readFileSync(claudeMd, "utf8");
      console.log(
        (content.includes("OpenSddRag") ? chalk.green("    ✓") : chalk.yellow("    !")) +
        " CLAUDE.md" +
        (content.includes("OpenSddRag") ? "" : "  (missing OpenSddRag section)")
      );
    } else {
      console.log(chalk.dim("    –") + " CLAUDE.md not found");
    }

    // ── Server health ─────────────────────────────────────────────────────────
    console.log(chalk.dim("\n  Server:"));
    process.stdout.write(`    ${serverUrl} ... `);
    try {
      await checkHealth(serverUrl);
      console.log(chalk.green("online ✓"));

      if (slug) {
        const projects = await listProjects(serverUrl);
        const mine = projects.find((p) => p.slug === slug);
        console.log(
          (mine ? chalk.green("    ✓") : chalk.yellow("    !")) +
          ` project '${slug}' ` +
          (mine ? `registered (id: ${mine.id})` : "NOT registered in database — run: opensddrag init")
        );
      }
    } catch {
      console.log(chalk.red("offline ✗"));
      console.log(chalk.dim("    docker compose up -d  or  opensddrag server start --transport sse"));
    }

    console.log("");
  });
