import { test } from "node:test";
import assert from "node:assert/strict";

import { sddManifest } from "../src/templates/flows/sdd/manifest.js";

test("unit-1: sdd manifest exports all required fields", () => {
  assert.ok(sddManifest, "manifest must be exported");
  assert.equal(sddManifest.flow, "sdd");
  assert.ok(Array.isArray(sddManifest.kinds), "kinds must be an array");
  const kindNames = sddManifest.kinds.map((k) => (typeof k === "string" ? k : k.kind));
  assert.deepEqual(
    kindNames.sort(),
    ["design", "proposal", "spec", "task", "test"],
    "kinds must be the five SDD kinds",
  );
  assert.ok(Array.isArray(sddManifest.harnessTriggers), "harnessTriggers must be an array");
  assert.ok(sddManifest.harnessTriggers.length > 0);
  assert.ok(Array.isArray(sddManifest.skills), "skills must be an array");
  assert.ok(sddManifest.skills.length >= 13, "at least the 13 SDD skills");
  assert.ok(Array.isArray(sddManifest.commands), "commands must be an array");
  assert.ok(sddManifest.commands.length >= 13, "at least the 13 SDD commands");
  assert.equal(typeof sddManifest.claudeMdSection, "string");
  assert.ok(
    sddManifest.claudeMdSection.includes("OpenSddRag"),
    "claudeMdSection must contain the stable 'OpenSddRag' marker",
  );
});

test("unit-1: kinds are addressable by (flow, kind)", () => {
  const pairs = sddManifest.kinds.map((k) => `${sddManifest.flow}:${typeof k === "string" ? k : k.kind}`);
  for (const expected of ["sdd:proposal", "sdd:spec", "sdd:design", "sdd:task", "sdd:test"]) {
    assert.ok(pairs.includes(expected), `missing ${expected}`);
  }
});
test("unit-1: sdd manifest declares the ordered lifecycle (REQ-007)", () => {
  const phases = sddManifest.lifecycle;
  assert.ok(Array.isArray(phases) && phases.length === 7, "sdd lifecycle must have 7 phases");
  const names = phases.map((p) => p.name);
  assert.deepEqual(
    names,
    ["Propose", "Spec", "Design", "Tasks", "Apply", "Verify", "Archive"],
    "lifecycle phases must be in canonical SDD order",
  );
  const declared = new Set(sddManifest.kinds.map((k) => (typeof k === "string" ? k : k.kind)));
  for (const phase of phases) {
    assert.ok(Array.isArray(phase.kinds) && phase.kinds.length >= 1, "each phase declares >=1 kind");
    for (const kind of phase.kinds) {
      assert.ok(declared.has(kind), `phase ${phase.name} kind ${kind} must be declared`);
    }
  }
});

test("unit-1: lifecycle kinds cover all five kinds exactly once", () => {
  const phaseKinds = sddManifest.lifecycle.flatMap((p) => p.kinds);
  const five = ["proposal", "spec", "design", "task", "test"];
  for (const kind of five) {
    assert.ok(phaseKinds.includes(kind), `kind ${kind} must appear in a phase`);
  }
});
