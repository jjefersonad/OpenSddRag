import { test } from "node:test";
import assert from "node:assert/strict";

import { selectedDefaultFlow } from "../src/flows.js";
import { updateProject } from "../src/api.js";

test("unit-1: a single non-sdd flow is selected as the default", () => {
  assert.equal(typeof updateProject, "function", "api must export updateProject");
  assert.equal(selectedDefaultFlow([{ flow: "websec" }]), "websec");
  assert.equal(selectedDefaultFlow([{ flow: "docs" }]), "docs");
});

test("unit-2: sdd-only, mixed and empty selections do not change the default", () => {
  assert.equal(selectedDefaultFlow([{ flow: "sdd" }]), null);
  assert.equal(selectedDefaultFlow([{ flow: "sdd" }, { flow: "websec" }]), null);
  assert.equal(selectedDefaultFlow([]), null);
  assert.equal(selectedDefaultFlow(undefined), null);
});
