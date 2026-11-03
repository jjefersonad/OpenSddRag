import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readdirSync, existsSync, rmSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { installFlows, loadFlowManifest, registerManifests, toServerManifest } from "../src/flows.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SHIPPED_FLOWS = join(__dirname, "..", "src", "templates", "flows");
const SLUG = "test-change";
const SERVER = "http://localhost:8000";

const DOCS3 = {
  "manifest.js": `export const manifest = {
  flow: "docs",
  kinds: [{ kind: "doc" }],
  harnessTriggers: ["on_doc_publish"],
  skills: [],
  commands: [{ name: "draft" }, { name: "review" }, { name: "publish" }],
  claudeMdSection: "## OpenSddRag — docs\\nDocs body.",
};\n`,
  "commands/index.js": `export const getCommands = () => [
  { name: "draft", folder: "docs", content: "d1" },
  { name: "review", folder: "docs", content: "d2" },
  { name: "publish", folder: "docs", content: "d3" },
];
export const getOpenCodeCommands = getCommands;\n`,
};

function makeRoot(extra = {}) {
  const root = mkdtempSync(join(tmpdir(), "opsr-flows-"));
  try { symlinkSync(join(SHIPPED_FLOWS, "sdd"), join(root, "sdd"), "dir"); } catch {}
  for (const [slug, files] of Object.entries(extra)) {
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
function cleanup(p) { try { rmSync(p, { recursive: true, force: true }); } catch {} }

// ── Unit 1: manifest drives installation ─────────────────────────────────────

test("unit-1: a docs manifest with 3 commands yields exactly 3 docs command files", async () => {
  const root = makeRoot({ docs: DOCS3 });
  const cwd = mkdtempSync(join(tmpdir(), "opsr-cwd-"));
  try {
    const docs = await loadFlowManifest(root, "docs");
    await installFlows({
      cwd, flowsRoot: root, manifests: [docs], slug: SLUG, serverUrl: SERVER,
      tools: ["Claude Code"], projectName: "T",
    });
    const dir = join(cwd, ".claude", "commands", "opsr", "docs");
    assert.ok(existsSync(dir), "docs command dir exists");
    const files = readdirSync(dir).sort();
    assert.deepEqual(files, ["draft.md", "publish.md", "review.md"]);
  } finally {
    cleanup(root); cleanup(cwd);
  }
});

// ── Unit 2: registration with the server ─────────────────────────────────────

test("unit-2: non-sdd manifests are registered when the server is reachable", async () => {
  const registered = [];
  const result = await registerManifests({
    manifests: [{ flow: "sdd" }, { flow: "docs", kinds: [{ kind: "doc" }] }],
    registerFn: async (m) => { registered.push(m.flow); },
  });
  assert.deepEqual(registered, ["docs"], "sdd is server-built-in and must be skipped");
  assert.deepEqual(result.registered, ["docs"]);
  assert.deepEqual(result.skipped, []);
});

test("unit-2: unreachable server is a graceful skip, not fatal", async () => {
  const result = await registerManifests({
    manifests: [{ flow: "docs", kinds: [{ kind: "doc" }] }],
    registerFn: async () => { throw new Error("ECONNREFUSED"); },
  });
  assert.deepEqual(result.registered, []);
  assert.deepEqual(result.skipped, ["docs"]);
});

test("unit-2: manifest is converted to the server's snake_case shape", () => {
  const server = toServerManifest({
    flow: "docs",
    kinds: [{ kind: "doc", required_headings: ["## Objective"] }],
    harnessTriggers: ["on_doc_publish"],
    lifecycle: [{ name: "Draft", kinds: ["doc"] }],
    skills: ["draft"],
    commands: [{ name: "draft", folder: "docs" }],
    claudeMdSection: "## s",
  });
  assert.deepEqual(server, {
    flow: "docs",
    kinds: [{ kind: "doc", required_headings: ["## Objective"] }],
    harness_triggers: ["on_doc_publish"],
    lifecycle: [{ name: "Draft", kinds: ["doc"] }],
    skills: ["draft"],
    commands: [{ name: "draft", folder: "docs" }],
    claude_md_section: "## s",
  });
});