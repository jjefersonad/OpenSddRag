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