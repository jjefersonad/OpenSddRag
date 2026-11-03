import { useState } from "react";
import { optimistic } from "../../api/client";
import { setRuleEnabled } from "../../api/rules";
import type { HarnessRule } from "../../api/types";

const SEVERITY_COLOR: Record<string, string> = {
  error: "var(--color-danger)",
  warning: "var(--color-warn)",
  info: "var(--color-info)",
};

function Badge({ children, color }: { children: string; color?: string }) {
  return (
    <span
      className="label"
      style={{
        border: "1px solid var(--color-border)",
        borderRadius: "999px",
        padding: "2px 8px",
        color: color ?? "var(--color-text-secondary)",
      }}
    >
      {children}
    </span>
  );
}

/** One harness rule row with an optimistic enable/disable toggle (REQ-003). */
export default function RuleRow({ slug, rule }: { slug: string; rule: HarnessRule }) {
  const [enabled, setEnabled] = useState(rule.enabled);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    const next = !enabled;
    setError(null);
    try {
      await optimistic({
        apply: () => setEnabled(next),
        action: () => setRuleEnabled(slug, rule.id, next),
        rollback: () => setEnabled(enabled),
      });
    } catch {
      setError("Could not update the rule.");
    }
  }

  return (
    <div
      role="row"
      style={{
        display: "grid",
        gridTemplateColumns: "1fr auto auto auto auto",
        alignItems: "center",
        gap: "10px",
        padding: "10px 12px",
        borderBottom: "1px solid var(--color-border)",
        background: "var(--color-card)",
      }}
    >
      <span style={{ fontFamily: "var(--font-mono)" }}>{rule.name}</span>
      <Badge>{rule.trigger}</Badge>
      <Badge>{rule.category}</Badge>
      <Badge color={SEVERITY_COLOR[rule.severity]}>{rule.severity}</Badge>
      <input
        type="checkbox"
        checked={enabled}
        onChange={toggle}
        aria-label={`toggle ${rule.name}`}
      />
      {error ? (
        <span role="alert" style={{ gridColumn: "1 / -1", color: "var(--color-danger)" }}>
          {error}
        </span>
      ) : null}
    </div>
  );
}
