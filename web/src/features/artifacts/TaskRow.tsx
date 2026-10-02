import { useState } from "react";
import { optimistic } from "../../api/client";
import { setTaskDone } from "../../api/tasks";
import type { Artifact } from "../../api/types";

/** Task row with an optimistic done checkbox (web-dashboard-ui REQ-004). */
export default function TaskRow({ slug, task }: { slug: string; task: Artifact }) {
  const [done, setDone] = useState(Boolean(task.metadata?.done));
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    const next = !done;
    setError(null);
    try {
      await optimistic({
        apply: () => setDone(next),
        action: () => setTaskDone(slug, task.id, next),
        rollback: () => setDone(done),
      });
    } catch {
      setError("Could not update the task.");
    }
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        padding: "10px 12px",
        borderBottom: "1px solid var(--color-border)",
        background: "var(--color-card)",
      }}
    >
      <input
        type="checkbox"
        checked={done}
        onChange={toggle}
        aria-label={`toggle ${task.name}`}
      />
      <span style={{ fontFamily: "var(--font-mono)" }}>{task.name}</span>
      {error ? (
        <span role="alert" style={{ color: "var(--color-danger)" }}>
          {error}
        </span>
      ) : null}
    </div>
  );
}
