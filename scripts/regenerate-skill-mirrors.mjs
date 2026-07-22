#!/usr/bin/env node
/**
 * Regenerate the .claude/, .agents/ and .opencode/ SKILL.md mirrors from
 * client/src/templates/skills/*.js. Run after editing any template.
 *
 * This script is NOT shipped in the published package — it is the in-repo
 * mirror of what `init` does in user projects, executed with the local
 * `opensddrag` slug so the project's own agents pick up the changes.
 */
import { writeFileSync } from "node:fs";
import { mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "..");

const { getSkills, getOpenCodeSkills } = await import(
  resolve(repoRoot, "client/src/templates/skills/index.js")
);

const slug = "opensddrag";
const serverUrl = "http://localhost:8000";

const ccNote = `> **MCP server:** \`opensddrag\` (${serverUrl}) | **project_slug:** \`${slug}\`
> **Available tools:** \`create_artifact\`, \`read_artifact\`, \`list_artifacts\`, \`read_change_bundle\`, \`update_artifact\`, \`validate_artifact\`, \`link_artifacts\`, \`get_relationships\`, \`search_semantic\`, \`recall_episodes\`, \`get_working_context\`, \`update_working_context\`, \`record_trace\`, \`get_harness_checklist\`
> If these tools are not in your active tool list, the \`opensddrag\` MCP server is not connected — STOP and inform the user.

`;

const ocNote = `> **project_slug for every call:** \`${slug}\`

`;

function writeMirror(rootDir, skills) {
  for (const skill of skills) {
    const dir = resolve(repoRoot, rootDir, "skills", skill.name);
    mkdirSync(dir, { recursive: true });
    writeFileSync(resolve(dir, "SKILL.md"), skill.content);
    console.log(`  wrote ${rootDir}/skills/${skill.name}/SKILL.md`);
  }
}

// .claude and .agents share the same content (Claude Code header).
writeMirror(".claude", getSkills(slug, serverUrl));
writeMirror(".agents", getSkills(slug, serverUrl));
// .opencode uses its own header.
writeMirror(".opencode", getOpenCodeSkills(slug, serverUrl));
