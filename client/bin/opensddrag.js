#!/usr/bin/env node
import { program } from "commander";
import { createRequire } from "module";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { readFileSync } from "fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(readFileSync(join(__dirname, "../package.json"), "utf8"));

program
  .name("opensddrag")
  .description("Connect any project to the OpenSddRag SDD+Harness MCP server")
  .version(pkg.version);

const { initCommand } = await import("../src/commands/init.js");
const { statusCommand } = await import("../src/commands/status.js");

program.addCommand(initCommand);
program.addCommand(statusCommand);

program.parse();
