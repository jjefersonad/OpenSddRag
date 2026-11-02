/**
 * websec flow skills — aggregator.
 *
 * Each of the five websec skills lives in its own module exporting
 * { name, description, body(slug, note) }. This file wraps every body with the
 * Claude Code or OpenCode header (`note`) plus YAML frontmatter, so the workflow
 * is authored once per skill and the CC/OC pair is always in sync
 * (command-skill-separation-contract REQ-001). The public API —
 * getSkills(slug, serverUrl) and getOpenCodeSkills(slug, serverUrl) — matches the
 * SDD pack, so client/src/flows.js needs no edits.
 */

import { scopeSkill } from "./scope.js";
import { assessSkill } from "./assess.js";
import { validateSkill } from "./validate.js";
import { remediateSkill } from "./remediate.js";
import { reportSkill } from "./report.js";

const SKILLS = [scopeSkill, assessSkill, validateSkill, remediateSkill, reportSkill];

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
 * OpenCode skills — installed to .opencode/skills/. Same content; the header
 * names the OpenCode skill location so the agent loads the right file.
 */
export function getOpenCodeSkills(slug, serverUrl) {
  const note = `> **MCP server:** \`opensddrag\` (${serverUrl}) | **project_slug:** \`${slug}\`
> **Available tools:** \`create_artifact\`, \`read_artifact\`, \`list_artifacts\`, \`read_change_bundle\`, \`update_artifact\`, \`validate_artifact\`, \`link_artifacts\`, \`get_relationships\`, \`search_semantic\`, \`recall_episodes\`, \`get_working_context\`, \`update_working_context\`, \`record_trace\`, \`get_harness_checklist\`
> If these tools are not in your active tool list, the \`opensddrag\` MCP server is not connected — STOP and inform the user.\n\n`;

  return SKILLS.map((skill) => ({
    name: skill.name,
    content: `${frontmatter(skill.name, skill.description)}${skill.body(slug, note)}`,
  }));
}
