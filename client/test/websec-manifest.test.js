import { test } from "node:test";
import assert from "node:assert/strict";

import { websecManifest } from "../src/templates/flows/websec/manifest.js";

const kindName = (k) => (typeof k === "string" ? k : k.kind);
const kindByName = (name) => websecManifest.kinds.find((k) => kindName(k) === name);

test("unit-1: websec manifest declares the six kinds", () => {
  assert.ok(websecManifest, "manifest must be exported");
  assert.equal(websecManifest.flow, "websec");
  const names = websecManifest.kinds.map(kindName).sort();
  assert.deepEqual(
    names,
    ["engagement", "finding", "poc", "remediation", "report", "surface"],
    "kinds must be engagement, finding, poc, remediation, report, surface",
  );
});

test("unit-1: finding and engagement carry their required metadata keys", () => {
  const finding = kindByName("finding");
  for (const key of ["severity", "reference", "evidence"]) {
    assert.ok(
      finding.required_metadata_keys.includes(key),
      `finding must require metadata key ${key}`,
    );
  }
  const engagement = kindByName("engagement");
  for (const key of ["target", "authorization", "scope"]) {
    assert.ok(
      engagement.required_metadata_keys.includes(key),
      `engagement must require metadata key ${key}`,
    );
  }
});

test("unit-2: websec lifecycle references only declared kinds, in order", () => {
  const phases = websecManifest.lifecycle;
  assert.ok(Array.isArray(phases) && phases.length === 7, "lifecycle must have 7 phases");
  assert.deepEqual(
    phases.map((p) => p.name),
    ["Scope", "Recon", "Model", "Assess", "Validate", "Remediate", "Report"],
    "lifecycle phases must be in canonical websec order",
  );
  const declared = new Set(websecManifest.kinds.map(kindName));
  for (const phase of phases) {
    for (const kind of phase.kinds) {
      assert.ok(declared.has(kind), `phase ${phase.name} references undeclared kind ${kind}`);
    }
  }
});
