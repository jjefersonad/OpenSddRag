import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getProject } from "../../api/projects";
import type { ProjectDetailData } from "../../api/types";
import ArtifactsTab from "../artifacts/ArtifactsTab";
import TaskList from "../artifacts/TaskList";
import HarnessTab from "../harness/HarnessTab";
import OverviewTab from "./OverviewTab";

const TABS: { id: string; label: string; type?: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "proposal", label: "Proposal", type: "proposal" },
  { id: "specs", label: "Specs", type: "spec" },
  { id: "design", label: "Design", type: "design" },
  { id: "tasks", label: "Tasks", type: "task" },
  { id: "harness", label: "Harness" },
];

/** Project detail shell with the six SDD tabs and summary-count badges
 *  (project-management REQ-003; design D2). */
export default function ProjectDetail() {
  const { slug } = useParams();
  const [project, setProject] = useState<ProjectDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    let active = true;
    if (!slug) return;
    setProject(null);
    setError(null);
    getProject(slug)
      .then((data) => {
        if (active) setProject(data);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "failed to load project");
      });
    return () => {
      active = false;
    };
  }, [slug]);

  if (error) return <p role="alert">{error}</p>;
  if (!project) return <p>Loading…</p>;

  return (
    <section>
      <h1 style={{ margin: "0 0 16px", fontSize: "20px" }}>{project.name ?? project.slug}</h1>
      <nav role="tablist" style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        {TABS.map((entry) => {
          const count = entry.type ? project.summary?.[entry.type] : undefined;
          return (
            <button
              key={entry.id}
              role="tab"
              aria-selected={tab === entry.id}
              onClick={() => setTab(entry.id)}
              style={{
                background: tab === entry.id ? "var(--color-card)" : "transparent",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                padding: "6px 12px",
                color: "var(--color-text-primary)",
                cursor: "pointer",
              }}
            >
              {entry.label}
              {typeof count === "number" ? (
                <span className="slug" style={{ marginLeft: "6px", color: "var(--color-accent)" }}>
                  {count}
                </span>
              ) : null}
            </button>
          );
        })}
      </nav>
      <div role="tabpanel">{renderTabContent(project, slug ?? "", tab)}</div>
    </section>
  );
}

function renderTabContent(project: ProjectDetailData, slug: string, tab: string) {
  switch (tab) {
    case "overview":
      return <OverviewTab project={project} />;
    case "proposal":
      return <ArtifactsTab slug={slug} type="proposal" />;
    case "specs":
      return <ArtifactsTab slug={slug} type="spec" />;
    case "design":
      return <ArtifactsTab slug={slug} type="design" />;
    case "tasks":
      return <TaskList slug={slug} />;
    case "harness":
      return <HarnessTab slug={slug} />;
    default:
      return null;
  }
}
