import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import {
  listAvailableFlows,
  parseFlowArg,
  loadFlowManifest,
  resolveSelectedFlows,
  installFlows,
  ManifestError,
} from "../src/flows.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SHIPPED_FLOWS = join(__dirname, "..", "src", "templates", "flows");
const golden = JSON.parse(
  readFileSync(join(__dirname, "fixtures", "sdd-templates.golden.json"), "utf8"),
);

const SLUG = "test-change";
const SERVER = "http://localhost:8000";

/** Build a temp flows root: symlink the shipped sdd pack + add extra packs. */
function makeFlowsRoot(extraPacks = {}) {
  const root = mkdtempSync(join(tmpdir(), "opsr-flows-"));
  mkdirSync(root, { recursive: true });
  // sdd: symlink to the shipped pack
  try {
    symlinkSync(join(SHIPPED_FLOWS, "sdd"), join(root, "sdd"), "dir");
  } catch {
    // symlink unsupported — skip
  }
  for (const [slug, files] of Object.entries(extraPacks)) {
    const dir = join(root, slug);
    mkdirSync(dir, { recursive: true });
    for (const [rel, content] of Object.entries(files)) {
      const p = join(dir, rel);
      mkdirSync(dirname(p), { recursive: true });
      writeFileSync(p, content);
    }
  }
  return root;
}

const DOCS_PACK = {
  "manifest.js": `export const manifest = {
  flow: "docs",
  kinds: [{ kind: "doc" }],
  harnessTriggers: ["on_doc_publish"],
  skills: ["opensddrag-docs-draft"],
  commands: [{ name: "draft", folder: "docs" }],
  claudeMdSection: "## OpenSddRag — docs flow\\nDocs marker.",
};\n`,
  "skills/index.js": `export const getSkills = (slug, serverUrl) => [{ name: "opensddrag-docs-draft", content: "DOCS SKILL " + slug }];
export const getOpenCodeSkills = (slug, serverUrl) => [{ name: "opensddrag-docs-draft", content: "DOCS OC SKILL " + slug }];\n`,
  "commands/index.js": `export const getCommands = (slug, serverUrl) => [{ folder: "opsr/docs", name: "draft", content: "DOCS CMD " + slug }];
export const getOpenCodeCommands = (slug, serverUrl) => [{ folder: "opsr/docs", name: "draft", content: "DOCS OC CMD " + slug }];\n`,
};

const BROKEN_PACK = {
  "manifest.js": `export const manifest = { flow: "broken", claudeMdSection: "x" };\n`,
};

function cleanup(root) {
  try { rmSync(root, { recursive: true, force: true }); } catch {}
}

// ── Unit 1: default init unchanged ───────────────────────────────────────────

test("unit-1: resolveSelectedFlows defaults to sdd alone with --yes", async () => {
  const root = makeFlowsRoot();
  try {
    const manifests = await resolveSelectedFlows({ yes: true, flowsRoot: root });
    assert.deepEqual(manifests.map((m) => m.flow), ["sdd"]);
  } finally {
    cleanup(root);
  }
});

test("unit-1: default sdd install is byte-identical to v0.1.1", async () => {
  const root = makeFlowsRoot();
  const cwd = mkdtempSync(join(tmpdir(), "opsr-cwd-"));
  try {
    const manifests = await resolveSelectedFlows({ yes: true, flowsRoot: root });
    await installFlows({
      cwd, flowsRoot: root, manifests, slug: SLUG, serverUrl: SERVER,
      tools: ["Claude Code"],
    });
    // skill files byte-identical
    for (const skill of golden.skills) {
      const p = join(cwd, ".claude", "skills", skill.name, "SKILL.md");
      assert.ok(existsSync(p), `missing ${p}`);
      assert.equal(readFileSync(p, "utf8"), skill.content, `skill ${skill.name} drifted`);
    }
    // command files byte-identical
    for (const cmd of golden.commands) {
      const p = join(cwd, ".claude", "commands", cmd.folder, `${cmd.name}.md`);
      assert.ok(existsSync(p), `missing ${p}`);
      assert.equal(readFileSync(p, "utf8"), cmd.content, `command ${cmd.name} drifted`);
    }
  } finally {
    cleanup(root);
    cleanup(cwd);
  }
});

// ── Unit 2: multi-flow init ──────────────────────────────────────────────────

test("unit-2: init --flow sdd,docs installs both flows only", async () => {
  const root = makeFlowsRoot({ docs: DOCS_PACK });
  const cwd = mkdtempSync(join(tmpdir(), "opsr-cwd-"));
  try {
    const manifests = await resolveSelectedFlows({ flowArg: "sdd,docs", flowsRoot: root });
    assert.deepEqual(manifests.map((m) => m.flow), ["sdd", "docs"]);
    await installFlows({
      cwd, flowsRoot: root, manifests, slug: SLUG, serverUrl: SERVER,
      tools: ["Claude Code"],
    });
    // docs files exist
    assert.ok(existsSync(join(cwd, ".claude", "skills", "opensddrag-docs-draft", "SKILL.md")));
    assert.ok(existsSync(join(cwd, ".claude", "commands", "opsr", "docs", "draft.md")));
    // both claudeMd sections appended
    const claudeMd = readFileSync(join(cwd, "CLAUDE.md"), "utf8");
    assert.ok(claudeMd.includes("OpenSddRag"), "sdd section present");
    assert.ok(claudeMd.includes("Docs marker."), "docs section present");
    // unselected flow files absent
    assert.ok(!existsSync(join(cwd, ".claude", "skills", "opensddrag-audit")), "unselected flow must not appear");
  } finally {
    cleanup(root);
    cleanup(cwd);
  }
});

// ── Unit 3: malformed manifest aborts ────────────────────────────────────────

test("unit-3: manifest missing kinds is rejected with a named diagnostic", async () => {
  const root = makeFlowsRoot({ broken: BROKEN_PACK });
  try {
    await assert.rejects(
      () => loadFlowManifest(root, "broken"),
      (err) => err instanceof ManifestError && /kinds/.test(err.message),
    );
    await assert.rejects(
      () => resolveSelectedFlows({ flowArg: "broken", flowsRoot: root }),
      (err) => /kinds/.test(err.message),
    );
  } finally {
    cleanup(root);
  }
});

test("unit-3: malformed manifest writes no files", async () => {
  const root = makeFlowsRoot({ broken: BROKEN_PACK });
  const cwd = mkdtempSync(join(tmpdir(), "opsr-cwd-"));
  try {
    await assert.rejects(() => resolveSelectedFlows({ flowArg: "broken", flowsRoot: root }));
    // nothing was installed — cwd untouched
    assert.ok(!existsSync(join(cwd, ".claude")), "no skill files before validation");
    assert.ok(!existsSync(join(cwd, "CLAUDE.md")), "no CLAUDE.md before validation");
  } finally {
    cleanup(root);
    cleanup(cwd);
  }
});

// ── Unit 4: interactive selection ────────────────────────────────────────────

test("unit-4: interactive multi-select is offered with sdd pre-selected", async () => {
  const root = makeFlowsRoot({ docs: DOCS_PACK });
  let captured = null;
  try {
    const manifests = await resolveSelectedFlows({
      yes: false,
      flowsRoot: root,
      checkboxFn: async ({ choices }) => {
        captured = choices;
        return ["sdd"]; // user keeps default
      },
    });
    assert.ok(captured, "checkbox prompt must be invoked");
    const sddChoice = captured.find((c) => c.value === "sdd");
    assert.equal(sddChoice.checked, true, "sdd must be pre-selected");
    assert.deepEqual(manifests.map((m) => m.flow), ["sdd"]);
  } finally {
    cleanup(root);
  }
});

test("unit-4: selecting none aborts without installs", async () => {
  const root = makeFlowsRoot();
  try {
    const manifests = await resolveSelectedFlows({
      yes: false,
      flowsRoot: root,
      checkboxFn: async () => [],
    });
    assert.deepEqual(manifests, []);
  } finally {
    cleanup(root);
  }
});

test("parseFlowArg splits and trims", () => {
  assert.deepEqual(parseFlowArg("sdd, docs"), ["sdd", "docs"]);
  assert.deepEqual(parseFlowArg("sdd"), ["sdd"]);
});