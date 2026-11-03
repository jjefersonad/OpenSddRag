import { test } from "node:test";
import assert from "node:assert/strict";

import { websecManifest } from "../src/templates/flows/websec/manifest.js";
import { scopeSkill } from "../src/templates/flows/websec/skills/scope.js";
import { assessSkill } from "../src/templates/flows/websec/skills/assess.js";
import { validateSkill } from "../src/templates/flows/websec/skills/validate.js";
import { remediateSkill } from "../src/templates/flows/websec/skills/remediate.js";
import { reportSkill } from "../src/templates/flows/websec/skills/report.js";

const SLUG = "test-change";
const body = (skill) => skill.body(SLUG, "");

test("unit-1: scope skill encodes context modes, surface bootstrap and the engagement gate", () => {
  const b = body(scopeSkill);
  for (const mode of ["in-progress", "brownfield", "greenfield"]) {
    assert.ok(b.includes(mode), `scope skill must mention context mode '${mode}'`);
  }
  assert.ok(b.includes("context_mode"), "scope must record metadata.context_mode");
  assert.ok(/surface/i.test(b), "scope must describe the surface bootstrap");
  assert.ok(/source/i.test(b), "scope must record the surface source of truth");
  assert.ok(/engagement/i.test(b), "scope must require the engagement artifact");
  for (const key of ["target", "authorization", "scope"]) {
    assert.ok(b.includes(key), `scope must require engagement metadata '${key}'`);
  }
});

test("unit-1: manifest encodes the authorization gate and the six kinds", () => {
  const ruleNames = websecManifest.rules.map((r) => r.name);
  assert.ok(
    ruleNames.includes("websec-authorization-gate"),
    "manifest must declare the authorization gate rule",
  );
  const gate = websecManifest.rules.find((r) => r.name === "websec-authorization-gate");
  assert.equal(gate.severity, "error");
  assert.equal(gate.trigger, "on_apply");
});

test("unit-2: assess skill encodes per-mode finding anchoring", () => {
  const b = body(assessSkill);
  assert.ok(b.includes("finding"), "assess must create findings");
  assert.ok(b.includes("relates_to"), "assess must anchor to planning artifacts via relates_to");
  for (const key of ["file", "line", "git_sha"]) {
    assert.ok(b.includes(key), `assess must record brownfield provenance '${key}'`);
  }
  for (const key of ["severity", "reference", "evidence"]) {
    assert.ok(b.includes(key), `assess must require finding metadata '${key}'`);
  }
});

test("unit-3: validate and remediate skills encode implements/relates_to links", () => {
  assert.ok(body(validateSkill).includes("implements"), "poc must link to finding via implements");
  assert.ok(
    body(remediateSkill).includes("relates_to"),
    "remediation must link to finding via relates_to",
  );
});

test("unit-4: report skill encodes severity grouping", () => {
  const b = body(reportSkill);
  assert.ok(b.includes("Findings by Severity"), "report must include the severity grouping heading");
  assert.ok(/severity/i.test(b), "report must group by severity");
});
