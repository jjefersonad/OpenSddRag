/**
 * Flow selection + installation (client-cli REQ-010 / REQ-011).
 *
 * A flow is a named pack under `src/templates/flows/<slug>/` with:
 *   - manifest.js  → { flow, kinds, harnessTriggers, skills, commands, claudeMdSection }
 *   - skills/      → getSkills / getOpenCodeSkills
 *   - commands/    → getCommands / getOpenCodeCommands
 *
 * `init --flow <slug[,slug]>` selects packs; `--yes` without `--flow`
 * defaults to `sdd` alone (byte-identical to v0.1.1); otherwise an
 * interactive multi-select is offered. A manifest missing `flow` or
 * `kinds` aborts with a diagnostic naming the field, before any file is
 * written.
 */

import { readdirSync, existsSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import {
  renderClaudeMdStandalone,
  upsertClaudeMdBlock,
} from "./templates/claude-md.js";
import { getHarnessSkill, getOpenCodeHarnessSkill } from "./templates/skill-md.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
export const DEFAULT_FLOWS_ROOT = join(__dirname, "templates", "flows");

/**
 * Skill identifier for a flow (client-cli REQ-004 MODIFIED).
 *   sdd → unchanged (`opensddrag-<command>`)
 *   any non-sdd flow f → `opensddrag-<f>-<command>` (idempotent)
 */
export function flowSkillId(flow, rawName) {
  if (flow === "sdd") return rawName;
  let command = rawName.replace(/^opensddrag-/, "");
  command = command.replace(new RegExp(`^${flow}-`), "");
  return `opensddrag-${flow}-${command}`;
}

/**
 * Command destination folder (client-cli REQ-005 MODIFIED).
 *   sdd → the pack's own folder (`opsr`) — bare `/opsr:<command>`
 *   non-sdd flow f → `opsr/<f>` (invoked `/opsr:<f>:<command>`)
 */
export function flowCommandFolder(flow, rawFolder) {
  if (flow === "sdd") return rawFolder;
  return `opsr/${flow}`;
}

/** Convert a client (camelCase) manifest to the server's snake_case shape. */
export function toServerManifest(manifest) {
  return {
    flow: manifest.flow,
    kinds: manifest.kinds || [],
    harness_triggers: manifest.harnessTriggers || [],
    skills: manifest.skills || [],
    commands: manifest.commands || [],
    claude_md_section: manifest.claudeMdSection || "",
  };
}

/**
 * Register selected non-`sdd` manifests with the server (client-cli REQ-011).
 *
 * `sdd` is registered by the server itself, so it is skipped. Registration
 * is best-effort: `init` must still write files and exit 0 when the server
 * is unreachable, so a failing `registerFn` is recorded as `skipped`, not
 * thrown (flow-registry REQ-002 ingestion is idempotent server-side).
 */
export async function registerManifests({ manifests, registerFn }) {
  const registered = [];
  const skipped = [];
  for (const manifest of manifests) {
    if (!registerFn) { skipped.push(manifest.flow); continue; }
    if (manifest.flow === "sdd") continue; // server-built-in
    try {
      await registerFn(manifest);
      registered.push(manifest.flow);
    } catch {
      skipped.push(manifest.flow);
    }
  }
  return { registered, skipped };
}

/** A manifest missing a required field (flow-registry REQ-001 abort). */
export class ManifestError extends Error {
  constructor(field) {
    super(`Manifest is missing required field: ${field}`);
    this.name = "ManifestError";
    this.field = field;
  }
}

/** Split a `--flow` argument value into slugs. */
export function parseFlowArg(value) {
  if (!value) return [];
  return String(value)
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Slugs of the flow packs available under `flowsRoot` (dirs with manifest.js). */
export function listAvailableFlows(flowsRoot = DEFAULT_FLOWS_ROOT) {
  if (!existsSync(flowsRoot)) return [];
  return readdirSync(flowsRoot)
    .filter((name) => existsSync(join(flowsRoot, name, "manifest.js")))
    .sort();
}

/** Load and validate a flow manifest (requires `flow` and non-empty `kinds`). */
export async function loadFlowManifest(flowsRoot, slug) {
  const manifestPath = join(flowsRoot, slug, "manifest.js");
  if (!existsSync(manifestPath)) {
    throw new ManifestError("manifest.js");
  }
  const mod = await import(pathToFileURL(manifestPath).href);
  const manifest = mod.manifest || mod.sddManifest || mod.default;
  if (!manifest || !manifest.flow) throw new ManifestError("flow");
  if (!Array.isArray(manifest.kinds) || manifest.kinds.length === 0) {
    throw new ManifestError("kinds");
  }
  return manifest;
}

/**
 * Resolve which flows to install.
 *   - explicit `flowArg` → parse, load and validate each (aborts on bad manifest)
 *   - `yes` and no `flowArg` → sdd alone (v0.1.1 default)
 *   - otherwise interactive multi-select (sdd pre-selected); empty ⇒ []
 */
export async function resolveSelectedFlows({
  flowArg,
  yes = false,
  flowsRoot = DEFAULT_FLOWS_ROOT,
  checkboxFn,
} = {}) {
  if (flowArg) {
    const slugs = parseFlowArg(flowArg);
    const manifests = [];
    for (const slug of slugs) manifests.push(await loadFlowManifest(flowsRoot, slug));
    return manifests;
  }
  if (yes) return [await loadFlowManifest(flowsRoot, "sdd")];

  const available = listAvailableFlows(flowsRoot);
  const choices = available.map((slug) => ({
    name: slug,
    value: slug,
    checked: slug === "sdd",
  }));
  const prompt = checkboxFn || (await import("@inquirer/prompts")).checkbox;
  const selected = await prompt({ message: "Which flows to install?", choices });
  const manifests = [];
  for (const slug of selected) manifests.push(await loadFlowManifest(flowsRoot, slug));
  return manifests;
}

async function importPack(flowsRoot, slug, relPath) {
  const p = join(flowsRoot, slug, relPath);
  if (!existsSync(p)) return null;
  return import(pathToFileURL(p).href);
}

/**
 * Install every selected flow's skills, commands and CLAUDE.md section.
 * Returns a summary { skills, commands, claudeMd }.
 *
 * `sdd` keeps its v0.1.1 output exactly (bare `/opsr:*` commands, the
 * `opensddrag-harness` skill, the legacy CLAUDE.md block). Non-`sdd` flows
 * render from their pack modules and append their own `claudeMdSection`.
 */
export async function installFlows({
  cwd,
  flowsRoot = DEFAULT_FLOWS_ROOT,
  manifests,
  slug,
  serverUrl,
  tools,
  projectName,
}) {
  const summary = { skills: 0, commands: 0, claudeMd: [], claudeMdActions: [] };

  for (const manifest of manifests) {
    const flow = manifest.flow;
    const packSkills = await importPack(flowsRoot, flow, "skills/index.js");
    const packCommands = await importPack(flowsRoot, flow, "commands/index.js");

    // ── Skills ──────────────────────────────────────────────────────────────
    const skillRoots = [];
    if (tools.includes("Claude Code")) {
      skillRoots.push({ root: join(cwd, ".claude", "skills"), render: packSkills?.getSkills });
      skillRoots.push({ root: join(cwd, ".agents", "skills"), render: packSkills?.getSkills });
    }
    if (tools.includes("OpenCode")) {
      skillRoots.push({ root: join(cwd, ".opencode", "skills"), render: packSkills?.getOpenCodeSkills });
    }

    for (const { root, render } of skillRoots) {
      if (!render) continue;
      const skills = render(slug, serverUrl);
      for (const skill of skills) {
        const id = flowSkillId(flow, skill.name);
        const dir = join(root, id);
        mkdirSync(dir, { recursive: true });
        writeFileSync(join(dir, "SKILL.md"), skill.content);
        summary.skills += 1;
      }
      // The harness-management skill is part of the SDD pack only.
      if (flow === "sdd") {
        const harness =
          root.includes(".opencode")
            ? getOpenCodeHarnessSkill({ slug, serverUrl })
            : getHarnessSkill({ slug, serverUrl });
        const hdir = join(root, "opensddrag-harness");
        mkdirSync(hdir, { recursive: true });
        writeFileSync(join(hdir, "SKILL.md"), harness);
        summary.skills += 1;
      }
    }

    // ── Slash commands ──────────────────────────────────────────────────────
    if (tools.includes("Claude Code") && packCommands?.getCommands) {
      for (const cmd of packCommands.getCommands(slug, serverUrl)) {
        const dir = join(cwd, ".claude", "commands", flowCommandFolder(flow, cmd.folder));
        mkdirSync(dir, { recursive: true });
        writeFileSync(join(dir, `${cmd.name}.md`), cmd.content);
        summary.commands += 1;
      }
    }
    if (tools.includes("OpenCode") && packCommands?.getOpenCodeCommands) {
      for (const cmd of packCommands.getOpenCodeCommands(slug, serverUrl)) {
        const dir = join(cwd, ".opencode", "commands", flowCommandFolder(flow, cmd.folder));
        mkdirSync(dir, { recursive: true });
        writeFileSync(join(dir, `${cmd.name}.md`), cmd.content);
        summary.commands += 1;
      }
    }

    // ── CLAUDE.md section ───────────────────────────────────────────────────
    const claudeMdPath = join(cwd, "CLAUDE.md");
    if (flow === "sdd") {
      if (existsSync(claudeMdPath)) {
        const before = readFileSync(claudeMdPath, "utf8");
        const { content } = upsertClaudeMdBlock(before, { slug, serverUrl });
        writeFileSync(claudeMdPath, content);
        summary.claudeMdActions.push({
          flow,
          action: content === before ? "already" : "updated",
        });
      } else {
        writeFileSync(claudeMdPath, renderClaudeMdStandalone({ projectName: projectName || slug, slug, serverUrl }));
        summary.claudeMdActions.push({ flow, action: "created" });
      }
    } else if (manifest.claudeMdSection) {
      const marker = `opensddrag:flow:${flow}`;
      const existing = existsSync(claudeMdPath) ? readFileSync(claudeMdPath, "utf8") : "";
      if (!existing.includes(marker)) {
        const section = `<!-- ${marker} -->\n${manifest.claudeMdSection}\n`;
        writeFileSync(claudeMdPath, (existing ? existing + "\n" : "") + section);
        summary.claudeMdActions.push({ flow, action: "appended" });
      } else {
        summary.claudeMdActions.push({ flow, action: "already" });
      }
    }
    summary.claudeMd.push(flow);
  }

  return summary;
}