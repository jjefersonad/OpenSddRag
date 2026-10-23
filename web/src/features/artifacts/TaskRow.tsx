import { useState } from "react";
import { optimistic } from "../../api/client";
import { setTaskDone } from "../../api/tasks";
import type { Artifact } from "../../api/types";
import MarkdownBody from "../../components/MarkdownBody";
import { displayTitle, parseSections } from "./parsers";

function isTaskDone(task: Artifact): boolean {
  return task.status === "archived" || Boolean(task.metadata?.done);
}

/** Task row with an optimistic done checkbox (web-dashboard-ui REQ-004 + REQ-015). */
export default function TaskRow({
  slug,
  task,
  readOnly = false,
}: {
  slug: string;
  task: Artifact;
  readOnly?: boolean;
}) {
  const archived = task.status === "archived";
  const [done, setDone] = useState(isTaskDone(task));
  const [error, setError] = useState<string | null>(null);
  const changeName = typeof task.metadata?.change_name === "string" ? task.metadata.change_name : "";
  const title = displayTitle({
    type: "task",
    name: task.name,
    content: task.content,
    changeName,
  });
  const sections = parseSections(task.content ?? "", ["Goal", "Steps"]);

  async function toggle() {
    if (readOnly || archived) return;
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
      data-testid={`task-row-${task.name}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "6px",
        padding: "10px 12px",
        borderBottom: "1px solid var(--color-border)",
        background: "var(--color-card)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <input
          type="checkbox"
          checked={done}
          disabled={readOnly || archived}
          onChange={toggle}
          aria-label={`toggle ${task.name}`}
        />
        <span style={{ fontSize: 14, fontWeight: 600, color: "#e8ebed" }}>{title}</span>
        {error ? (
          <span role="alert" style={{ color: "var(--color-danger)" }}>
            {error}
          </span>
        ) : null}
      </div>
      {sections["Goal"] ? (
        <MarkdownBody className="md-body-compact" testId={`task-goal-${task.name}`}>
          {sections["Goal"]}
        </MarkdownBody>
      ) : null}
      {sections["Steps"] ? <MarkdownBody className="md-body-compact">{sections["Steps"]}</MarkdownBody> : null}
    </div>
  );
}
