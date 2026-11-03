import { test } from "node:test";
import assert from "node:assert/strict";

import { getSkills, getOpenCodeSkills } from "../src/templates/flows/websec/skills/index.js";
import { getCommands, getOpenCodeCommands } from "../src/templates/flows/websec/commands/index.js";

const SLUG = "test-change";
const SERVER = "http://localhost:8000";
const FIVE = ["assess", "remediate", "report", "scope", "validate"];

const bare = (name) => name.replace(/^opensddrag-websec-/, "");

test("unit-1: websec skills expose the five commands", () => {
  for (const fn of [getSkills, getOpenCodeSkills]) {
    const skills = fn(SLUG, SERVER);
    assert.equal(skills.length, 5, "pack must expose exactly five skills");
    assert.deepEqual(
      skills.map((s) => bare(s.name)).sort(),
      FIVE,
      "skills must be the five websec commands",
    );
    for (const s of skills) {
      assert.ok(s.content && s.content.length > 0, `skill ${s.name} must have content`);
    }
  }
});

test("unit-1: websec commands expose the five commands", () => {
  for (const fn of [getCommands, getOpenCodeCommands]) {
    const cmds = fn(SLUG, SERVER);
    assert.equal(cmds.length, 5, "pack must expose exactly five commands");
    assert.deepEqual(
      cmds.map((c) => c.name).sort(),
      FIVE,
      "commands must be scope, assess, validate, remediate, report",
    );
    for (const c of cmds) {
      assert.ok(c.content && c.content.length > 0, `command ${c.name} must have content`);
    }
  }
});
