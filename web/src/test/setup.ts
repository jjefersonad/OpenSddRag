import "@testing-library/jest-dom/vitest";

// jsdom teardown removes `window` while react-dom's node scheduler may still
// dispatch queued immediates (Immediate.performWorkUntilDeadline). Shim the
// global reference so a late tick is a no-op instead of an unhandled
// ReferenceError. Harmless in a real browser (window always exists there).
const _g = globalThis as unknown as { window?: unknown };
if (typeof _g.window === "undefined") {
  _g.window = _g;
}
