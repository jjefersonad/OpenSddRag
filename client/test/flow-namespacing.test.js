import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { installFlows, loadFlowManifest } from "../src/flows.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SHIPPED_FLOWS = join(__dirname, "..", "src", "templates", "flows");
const SLUG = "test-change";
const SERVER = "http://localhost:8000";

// A docs pack whose renderers return SHORT command names — the prefixing and
// namespacing rules must be applied centrally by installFlows.
const DOCS_PACK = {
  "manifest.js": `export const manifest = {
  flow: "docs",
  kinds: [{ kind: "doc" }],
  harnessTriggers: [],
  skills: ["draft"],
  commands: [{ name: "draft" }],
  claudeMdSection: "## OpenSddRag — docs flow\\nDocs section body.",
};\n`,
  "skills/index.js": `export const getSkills = () => [{ name: "draft", content: "DOCS SKILL" }];
export const getOpenCodeSkills = () => [{ name: "draft", content: "DOCS OC SKILL" }];\n`,
  "commands/index.js": `export const getCommands = () => [{ name: "draft", folder: "docs", content: "DOCS CMD" }];
export const getOpenCodeCommands = () => [{ name: "draft", folder: "docs", content: "DOCS OC CMD" }];\n`,
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

async function manifestsFor(root, flowArg) {
  const slugs = flowArg.split(",").map((s) => s.trim());
  return Promise.all(slugs.map((s) => loadFlowManifest(root, s)));
}

function cleanup(p) { try { rmSync(p, { recursive: true, force: true }); } catch {} }

// ── Unit 1: non-SDD skill identifiers are prefixed ───────────────────────────

test("unit-1: non-sdd skills are written as opensddrag-<flow>-<command>", async () => {
  const root = makeRoot({ docs: DOCS_PACK });
  const cwd = mkdtempSync(join(tmpdir(), "opsr-cwd-"));
  try {
    await installFlows({
      cwd, flowsRoot: root, manifests: await manifestsFor(root, "sdd,docs"),
      slug: SLUG, serverUrl: SERVER, tools: ["Claude Code"], projectName: "T",
    });
    assert.ok(
      existsSync(join(cwd, ".claude", "skills", "opensddrag-docs-draft", "SKILL.md")),
      "docs skill must be opensddrag-docs-draft",
    );
    // SDD identifiers unchanged
    assert.ok(existsSync(join(cwd, ".claude", "skills", "opensddrag-propose", "SKILL.md")));
    assert.ok(!existsSync(join(cwd, ".claude", "skills", "draft")), "short name must not be used");
  } finally {
    cleanup(root); cleanup(cwd);
  }
});

// ── Unit 2: namespaced command layout ────────────────────────────────────────

test("unit-2: non-sdd commands go under opsr/<flow>/", async () => {
  const root = makeRoot({ docs: DOCS_PACK });
  const cwd = mkdtempSync(join(tmpdir(), "opsr-cwd-"));
  try {
    await installFlows({
      cwd, flowsRoot: root, manifests: await manifestsFor(root, "sdd,docs"),
      slug: SLUG, serverUrl: SERVER, tools: ["Claude Code"], projectName: "T",
    });
    assert.ok(
      existsSync(join(cwd, ".claude", "commands", "opsr", "docs", "draft.md")),
      "docs command must be at opsr/docs/draft.md",
    );
    assert.ok(!existsSync(join(cwd, ".claude", "commands", "docs", "draft.md")), "no top-level docs/");
  } finally {
    cleanup(root); cleanup(cwd);
  }
});

test("unit-2: sdd commands stay bare at opsr/<command>.md", async () => {
  const root = makeRoot();
  const cwd = mkdtempSync(join(tmpdir(), "opsr-cwd-"));
  try {
    await installFlows({
      cwd, flowsRoot: root, manifests: await manifestsFor(root, "sdd"),
      slug: SLUG, serverUrl: SERVER, tools: ["Claude Code"], projectName: "T",
    });
    assert.ok(existsSync(join(cwd, ".claude", "commands", "opsr", "propose.md")));
    assert.ok(!existsSync(join(cwd, ".claude", "commands", "opsr", "sdd")), "sdd must not be namespaced");
  } finally {
    cleanup(root); cleanup(cwd);
  }
});

// ── Unit 3: per-flow CLAUDE.md markers ───────────────────────────────────────

test("unit-3: re-running sdd does not re-append; docs appends only its section", async () => {
  const root = makeRoot({ docs: DOCS_PACK });
  const cwd = mkdtempSync(join(tmpdir(), "opsr-cwd-"));
  try {
    const sdd = await loadFlowManifest(root, "sdd");
    await installFlows({ cwd, flowsRoot: root, manifests: [sdd], slug: SLUG, serverUrl: SERVER, tools: ["Claude Code"], projectName: "T" });
    const afterFirst = readFileSync(join(cwd, "CLAUDE.md"), "utf8");
    assert.ok(afterFirst.includes("OpenSddRag"));

    // second sdd run — must not duplicate the sdd block
    const summary = await installFlows({ cwd, flowsRoot: root, manifests: [sdd], slug: SLUG, serverUrl: SERVER, tools: ["Claude Code"], projectName: "T" });
    const afterSecond = readFileSync(join(cwd, "CLAUDE.md"), "utf8");
    assert.equal(afterSecond, afterFirst, "sdd re-run must not change CLAUDE.md");
    assert.equal(
      (afterSecond.match(/OpenSddRag — SDD \+ Harness/g) || []).length,
      1,
      "sdd section must appear once",
    );
    assert.equal(summary.claudeMdActions.find((a) => a.flow === "sdd").action, "already");

    // docs appends ONLY its section
    const docs = await loadFlowManifest(root, "docs");
    await installFlows({ cwd, flowsRoot: root, manifests: [docs], slug: SLUG, serverUrl: SERVER, tools: ["Claude Code"], projectName: "T" });
    const withDocs = readFileSync(join(cwd, "CLAUDE.md"), "utf8");
    assert.ok(withDocs.includes("Docs section body."), "docs section appended");
    assert.equal(
      (withDocs.match(/OpenSddRag — SDD \+ Harness/g) || []).length,
      1,
      "sdd section untouched",
    );
  } finally {
    cleanup(root); cleanup(cwd);
  }
});

test("unit-3: docs section is not re-appended when its marker is present", async () => {
  const root = makeRoot({ docs: DOCS_PACK });
  const cwd = mkdtempSync(join(tmpdir(), "opsr-cwd-"));
  try {
    const docs = await loadFlowManifest(root, "docs");
    await installFlows({ cwd, flowsRoot: root, manifests: [docs], slug: SLUG, serverUrl: SERVER, tools: ["Claude Code"], projectName: "T" });
    const once = readFileSync(join(cwd, "CLAUDE.md"), "utf8");
    await installFlows({ cwd, flowsRoot: root, manifests: [docs], slug: SLUG, serverUrl: SERVER, tools: ["Claude Code"], projectName: "T" });
    const twice = readFileSync(join(cwd, "CLAUDE.md"), "utf8");
    assert.equal((twice.match(/Docs section body\./g) || []).length, 1, "docs section once");
  } finally {
    cleanup(root); cleanup(cwd);
  }
});