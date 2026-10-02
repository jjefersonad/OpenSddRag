import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// Unit-2: the template move is content-neutral — rendered output from the
// restructured `flows/sdd/` tree must be byte-identical to the v0.1.1 golden.

import { getSkills, getOpenCodeSkills } from "../src/templates/flows/sdd/skills/index.js";
import { getCommands } from "../src/templates/flows/sdd/commands/index.js";
import { getOpenCodeCommands } from "../src/templates/flows/sdd/commands/opencode.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const golden = JSON.parse(
  readFileSync(join(__dirname, "fixtures", "sdd-templates.golden.json"), "utf8"),
);

const slug = "test-change";
const serverUrl = "http://localhost:8000";

test("unit-2: skill content is byte-identical after the move", () => {
  const actual = getSkills(slug, serverUrl);
  assert.ok(actual.length >= 13, "at least 13 skill files");
  assert.deepEqual(actual, golden.skills);

  const ocActual = getOpenCodeSkills(slug, serverUrl);
  assert.deepEqual(ocActual, golden.openCodeSkills);
});

test("unit-2: command content is byte-identical after the move", () => {
  const actual = getCommands(slug, serverUrl);
  assert.ok(actual.length >= 13, "at least 13 command files");
  assert.deepEqual(actual, golden.commands);

  const ocActual = getOpenCodeCommands(slug, serverUrl);
  assert.deepEqual(ocActual, golden.openCodeCommands);
});

test("unit-2: sdd commands stay bare (no flow subfolder)", () => {
  const actual = getCommands(slug, serverUrl);
  for (const command of actual) {
    assert.notEqual(command.folder, "sdd", `command ${command.name} must not be namespaced under sdd/`);
  }
});