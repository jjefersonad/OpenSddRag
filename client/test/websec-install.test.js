import { test } from "node:test";
import assert from "node:assert/strict";
import {
  mkdtempSync,
  readdirSync,
  readFileSync,
  existsSync,
  rmSync,
  symlinkSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { installFlows, loadFlowManifest, registerManifests } from "../src/flows.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SHIPPED_FLOWS = join(__dirname, "..", "src", "templates", "flows");
const SLUG = "test-change";
const SERVER = "http://localhost:8000";
const FIVE = ["assess", "remediate", "report", "scope", "validate"];

/** Temp flows root symlinking the shipped sdd + websec packs. */
function makeRoot() {
  const root = mkdtempSync(join(tmpdir(), "opsr-websec-"));
  for (const slug of ["sdd", "websec"]) {
    try {
      symlinkSync(join(SHIPPED_FLOWS, slug), join(root, slug), "dir");
    } catch {
      // symlink unsupported — skip
    }
  }
  return root;
}
function cleanup(p) {
  try {
    rmSync(p, { recursive: true, force: true });
  } catch {}
}

test("unit-1: installFlows installs websec commands namespaced under opsr/websec", async () => {
  const root = makeRoot();
  const cwd = mkdtempSync(join(tmpdir(), "opsr-websec-proj-"));
  try {
    const manifest = await loadFlowManifest(root, "websec");
    await installFlows({
      cwd,
      flowsRoot: root,
      manifests: [manifest],
      slug: SLUG,
      serverUrl: SERVER,
      tools: ["Claude Code"],
    });

    const cmdDir = join(cwd, ".claude", "commands", "opsr", "websec");
    assert.ok(existsSync(cmdDir), "commands must be installed under opsr/websec");
    assert.deepEqual(
      readdirSync(cmdDir).sort(),
      FIVE.map((n) => `${n}.md`).sort(),
      "exactly the five websec commands must be written",
    );

    const skills = readdirSync(join(cwd, ".claude", "skills"));
    for (const cmd of FIVE) {
      assert.ok(
        skills.includes(`opensddrag-websec-${cmd}`),
        `skill opensddrag-websec-${cmd} must be installed`,
      );
    }

    assert.ok(
      !existsSync(join(cwd, ".claude", "commands", "opsr", "propose.md")),
      "bare /opsr:<command> SDD files MUST NOT be written for the websec flow",
    );
  } finally {
    cleanup(root);
    cleanup(cwd);
  }
});

test("unit-1: registerManifests registers the websec flow with the server", async () => {
  const root = makeRoot();
  try {
    const manifest = await loadFlowManifest(root, "websec");
    const calls = [];
    const { registered, skipped } = await registerManifests({
      manifests: [manifest],
      registerFn: async (m) => {
        calls.push(m.flow);
      },
    });
    assert.deepEqual(calls, ["websec"], "websec manifest must be registered");
    assert.deepEqual(registered, ["websec"]);
    assert.deepEqual(skipped, []);
  } finally {
    cleanup(root);
  }
});

test("unit-2: installFlows appends the websec CLAUDE.md section with its marker", async () => {
  const root = makeRoot();
  const cwd = mkdtempSync(join(tmpdir(), "opsr-websec-proj-"));
  try {
    const manifest = await loadFlowManifest(root, "websec");
    const args = { cwd, flowsRoot: root, manifests: [manifest], slug: SLUG, serverUrl: SERVER, tools: ["Claude Code"] };
    await installFlows(args);

    const claudePath = join(cwd, "CLAUDE.md");
    assert.ok(existsSync(claudePath), "CLAUDE.md must be created");
    const claude = readFileSync(claudePath, "utf8");
    assert.ok(
      claude.includes("opensddrag:flow:websec"),
      "the websec section marker must be present",
    );
    assert.ok(claude.includes("websec"), "the section must mention websec");

    await installFlows(args);
    const again = readFileSync(claudePath, "utf8");
    assert.equal(again, claude, "re-running init must not duplicate the section");
  } finally {
    cleanup(root);
    cleanup(cwd);
  }
});
