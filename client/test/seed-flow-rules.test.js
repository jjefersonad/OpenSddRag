import { test } from "node:test";
import assert from "node:assert/strict";

import { seedFlowRules } from "../src/flows.js";

const rule = (name) => ({
  name,
  trigger: "on_apply",
  category: "verification",
  severity: "error",
  instruction: `${name} instruction`,
});

test("unit-1: a manifest with rules seeds each rule via addRule", async () => {
  const calls = [];
  const addRuleFn = async (slug, r) => {
    calls.push([slug, r.name]);
  };
  const manifests = [{ flow: "websec", rules: [rule("gate-a"), rule("gate-b")] }];

  const result = await seedFlowRules({ manifests, addRuleFn });

  assert.deepEqual(calls, [
    ["websec", "gate-a"],
    ["websec", "gate-b"],
  ]);
  assert.deepEqual(result.seeded, ["gate-a", "gate-b"]);
  assert.deepEqual(result.skipped, []);
});

test("unit-2: a manifest without rules seeds no additional rules", async () => {
  const calls = [];
  const addRuleFn = async (slug, r) => {
    calls.push([slug, r.name]);
  };
  const manifests = [{ flow: "sdd", skills: ["opensddrag-propose"] }];

  const result = await seedFlowRules({ manifests, addRuleFn });

  assert.equal(calls.length, 0, "no rule must be seeded for a manifest without rules");
  assert.deepEqual(result.seeded, []);
  assert.deepEqual(result.skipped, []);
});

test("unit-2: rules are skipped, not thrown, when no addRule function is available", async () => {
  const manifests = [{ flow: "websec", rules: [rule("gate-a")] }];

  const result = await seedFlowRules({ manifests, addRuleFn: null });

  assert.deepEqual(result.seeded, []);
  assert.deepEqual(result.skipped, ["websec:gate-a"]);
});
