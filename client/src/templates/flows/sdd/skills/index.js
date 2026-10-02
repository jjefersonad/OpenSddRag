/**
 * OpenSddRag skill templates — aggregator.
 *
 * Each of the 13 SDD skills lives in its own module exporting
 * { name, description, body(slug, note) }. This file wraps every body with the
 * Claude Code or OpenCode header (`note`) plus YAML frontmatter, so the workflow
 * is authored once per skill and the CC/OC pair is always in sync
 * (command-skill-separation-contract REQ-001). The public API —
 * getSkills(slug, serverUrl) and getOpenCodeSkills(slug, serverUrl) — is
 * unchanged, so client/src/commands/init.js needs no edits.
 */

import { proposeSkill } from "./propose.js";
import { specSkill } from "./spec.js";
import { designSkill } from "./design.js";
import { tasksSkill } from "./tasks.js";
import { applySkill } from "./apply.js";
import { verifySkill } from "./verify.js";
import { syncSkill } from "./sync.js";
import { archiveSkill } from "./archive.js";
import { exploreSkill } from "./explore.js";
import { continueSkill } from "./continue.js";
import { statusSkill } from "./status.js";
import { flowSkill } from "./flow.js";
import { searchSkill } from "./search.js";

const SKILLS = [
  proposeSkill,
  specSkill,
  designSkill,
  tasksSkill,
  applySkill,
  verifySkill,
  syncSkill,
  archiveSkill,
  exploreSkill,
  continueSkill,
  statusSkill,
  flowSkill,
  searchSkill,
];

const frontmatter = (name, description) =>
  `---\nname: ${name}\ndescription: ${description}\n---\n\n`;

/**
 * Claude Code skills — installed to .claude/skills/ and .agents/skills/.
 * Header advertises the MCP server + tool list and the STOP-if-not-connected rule.
 */
export function getSkills(slug, serverUrl) {
  const note = `> **MCP server:** \`opensddrag\` (${serverUrl}) | **project_slug:** \`${slug}\`
> **Available tools:** \`create_artifact\`, \`read_artifact\`, \`list_artifacts\`, \`read_change_bundle\`, \`update_artifact\`, \`validate_artifact\`, \`link_artifacts\`, \`get_relationships\`, \`search_semantic\`, \`recall_episodes\`, \`get_working_context\`, \`update_working_context\`, \`record_trace\`, \`get_harness_checklist\`
> If these tools are not in your active tool list, the \`opensddrag\` MCP server is not connected — STOP and inform the user.\n\n`;

  return SKILLS.map((skill) => ({
    name: skill.name,
    content: `${frontmatter(skill.name, skill.description)}${skill.body(slug, note)}`,
  }));
}

/**
 * OpenCode skills — installed to .opencode/skills/.
 * Compact header (project_slug only); MCP tools are auto-available in OpenCode.
 */
export function getOpenCodeSkills(slug, _serverUrl) {
  const note = `> **project_slug for every call:** \`${slug}\`\n\n`;

  return SKILLS.map((skill) => ({
    name: skill.name,
    content: `${frontmatter(skill.name, skill.description)}${skill.body(slug, note)}`,
  }));
}
