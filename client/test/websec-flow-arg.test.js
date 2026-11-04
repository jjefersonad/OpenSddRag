import { test } from "node:test";
import assert from "node:assert/strict";

import { scopeSkill } from "../src/templates/flows/websec/skills/scope.js";
import { assessSkill } from "../src/templates/flows/websec/skills/assess.js";
import { validateSkill } from "../src/templates/flows/websec/skills/validate.js";
import { remediateSkill } from "../src/templates/flows/websec/skills/remediate.js";
import { reportSkill } from "../src/templates/flows/websec/skills/report.js";

const body = (skill) => skill.body("test-change", "");
const FLOW = 'flow="websec"';

test("unit-1: scope skill pins flow=websec on its create_artifact calls", () => {
  const b = body(scopeSkill);
  const creates = (b.match(/create_artifact\(/g) ?? []).length;
  const flows = (b.match(/flow="websec"/g) ?? []).length;
  assert.ok(creates >= 2, `scope should create engagement + surface (got ${creates})`);
  assert.ok(flows >= 2, `scope must pass flow="websec" on both creates (got ${flows})`);
});

test("unit-2: closing skills pin flow=websec on their create_artifact calls", () => {
  for (const skill of [assessSkill, validateSkill, remediateSkill, reportSkill]) {
    const b = body(skill);
    assert.ok(b.includes("create_artifact("), `${skill.name} should create artifacts`);
    assert.ok(b.includes(FLOW), `${skill.name} must pass flow="websec"`);
  }
});

test("unit-2: report scopes its findings listing to websec", () => {
  const b = body(reportSkill);
  // list_artifacts accepts a flow filter — the report should scope to websec
  assert.ok(/list_artifacts\([^)]*flow="websec"/.test(b), "report must list findings with flow=\"websec\"");
});
