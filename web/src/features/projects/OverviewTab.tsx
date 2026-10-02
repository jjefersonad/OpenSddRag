import type { ProjectDetailData } from "../../api/types";

/** Overview tab: the project's artifact summary counts (project-management REQ-003). */
export default function OverviewTab({ project }: { project: ProjectDetailData }) {
  const entries = Object.entries(project.summary ?? {});
  if (entries.length === 0) {
    return <p style={{ color: "var(--color-text-secondary)" }}>No artifacts yet.</p>;
  }
  return (
    <ul style={{ listStyle: "none", padding: 0, display: "flex", gap: "16px" }}>
      {entries.map(([type, count]) => (
        <li key={type} className="label">
          {type}: <span style={{ color: "var(--color-accent)" }}>{count}</span>
        </li>
      ))}
    </ul>
  );
}
