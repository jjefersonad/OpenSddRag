// Default harness rules seeded into every project at `opensddrag init` time.
// Unlike SDD skills (which can be global, project_id NULL), harness rules are
// always per-project (project_rules.project_id is NOT NULL) — there is no
// DB-wide `opensddrag-server init` seed for them. Seeding happens here, once
// per project, at the moment the project is guaranteed to exist.

export const DEFAULT_RULES = [
  {
    name: "tdd-first",
    trigger: "on_apply",
    category: "verification",
    severity: "error",
    instruction:
      "Before writing any production code for a testable unit (method/function) during /opsr:apply, " +
      "first create a test that fails covering the intended behavior (RED), then implement the minimal " +
      "code to pass (GREEN), then refactor while keeping it passing (REFACTOR). Stack-agnostic — applies " +
      "to pytest, vitest, jest, go test, or whatever runner the target project uses. Tasks with " +
      "metadata.test_exempt=true (and a stated reason in their content) are not subject to this gate.",
  },
];
