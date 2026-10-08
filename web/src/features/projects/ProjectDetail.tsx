import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getProject } from "../../api/projects";
import { listFlows } from "../../api/flows";
import type { FlowInfo, ProjectDetailData } from "../../api/types";
import ArtifactsTab from "../artifacts/ArtifactsTab";
import TaskList from "../artifacts/TaskList";
import HarnessTab from "../harness/HarnessTab";
import OverviewTab from "./OverviewTab";
import HierarchyTab from "../hierarchy/HierarchyTab";

const HARNESS_TAB = { id: "harness", label: "Harness" } as const;

/**
 * Project detail shell (REQ-014/REQ-015 multi-flow, design D7/D8): tabs are
 * generated from the registered kinds of the project's flows (via
 * GET /api/v1/flows) + a fixed Harness tab; one tab per kind, rendered once
 * per flow that declares it (flow-scoped when the project mixes flows).
 */
export default function ProjectDetail() {
  const { slug } = useParams();
  const [project, setProject] = useState<ProjectDetailData | null>(null);
  const [flows, setFlows] = useState<FlowInfo[]>([]);
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
    listFlows().then((f) => active && setFlows(f), () => active && setFlows([]));
    return () => {
      active = false;
    };
  }, [slug]);

  const tabs = useMemo(
    () => buildTabs(project, flows),
    [project, flows],
  );

  if (error) return <p role="alert">{error}</p>;
  if (!project) return <p>Loading…</p>;

  return (
    <section>
      <nav data-testid="detail-breadcrumb" aria-label="Breadcrumb" style={{ marginBottom: "12px", color: "var(--color-text-tertiary)", fontSize: "13px" }}>
        projects / {project.slug}
      </nav>
      <h1 style={{ margin: "0 0 16px", fontSize: "20px" }}>{project.name ?? project.slug}</h1>
      <nav role="tablist" style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
        {tabs.map((entry) => {
          const count = entry.type ? project.summary?.[entry.type] : undefined;
          return (
            <button
              key={entry.key}
              role="tab"
              aria-selected={tab === entry.key}
              onClick={() => setTab(entry.key)}
              style={{
                background: tab === entry.key ? "var(--color-card)" : "transparent",
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
        <HARNESS_TAB_RENDER entry={HARNESS_TAB} active={tab === HARNESS_TAB.id} onClick={() => setTab(HARNESS_TAB.id)} />
      </nav>
      <div role="tabpanel">
        {renderTabContent(project, slug ?? "", tab, flows, (nodeType: string) => {
          const target = buildTabs(project, flows).find((t) => t.type === nodeType && nodeType !== "test");
          setTab(target?.key ?? (nodeType === "test" ? "task" : "overview"));
        })}
      </div>
    </section>
  );
}

function HARNESS_TAB_RENDER({
  entry,
  active,
  onClick,
}: {
  entry: { id: string; label: string };
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      key={entry.id}
      role="tab"
      aria-selected={active}
      onClick={onClick}
      style={{
        background: active ? "var(--color-card)" : "transparent",
        border: "1px solid var(--color-border)",
        borderRadius: "8px",
        padding: "6px 12px",
        color: "var(--color-text-primary)",
        cursor: "pointer",
      }}
    >
      {entry.label}
    </button>
  );
}

interface TabEntry {
  key: string;
  label: string;
  type?: string;
  flow?: string;
}

function buildTabs(project: ProjectDetailData | null, flows: FlowInfo[]): TabEntry[] {
  const base: TabEntry[] = [
    { key: "overview", label: "Overview" },
    { key: "hierarchy", label: "Hierarchy" },
  ];
  const seen = new Set<string>();
  for (const flow of flows) {
    for (const kindEntry of flow.kinds) {
      const kind = kindEntry.kind;
      if (seen.has(kind)) continue;
      seen.add(kind);
      if (kind === "task") {
        base.push({ key: "task", label: labelFor(kind), type: kind });
      } else {
        base.push({ key: kind, label: labelFor(kind), type: kind });
      }
    }
  }
  return base;
}

function labelFor(kind: string): string {
  const singular = kind.endsWith("s") ? kind.slice(0, -1) : kind;
  const labels: Record<string, string> = {
    proposal: "Proposal",
    spec: "Specs",
    design: "Design",
    task: "Tasks",
    test: "Test scenarios",
  };
  return labels[kind] ?? singular.charAt(0).toUpperCase() + singular.slice(1);
}

function renderTabContent(
  project: ProjectDetailData,
  slug: string,
  tab: string,
  flows: FlowInfo[],
  onNavigate: (nodeType: string) => void,
) {
  switch (tab) {
    case "overview":
      return <OverviewTab slug={slug} />;
    case "hierarchy":
      return <HierarchyTab slug={slug} onNavigate={onNavigate} />;
    case "harness":
      return <HarnessWithCount slug={slug} />;
    default: {
      const entry = tabsOf(flows).find((t) => t.key === tab);
      const type = entry?.type ?? tab;
      if (type === "task") return <TaskList slug={slug} />;
      return <ArtifactsTab slug={slug} type={type} flow={entry?.flow} />;
    }
  }
}

function tabsOf(flows: FlowInfo[]): TabEntry[] {
  return buildTabs(null, flows);
}

function HarnessWithCount({ slug }: { slug: string }) {
  return <HarnessTab slug={slug} />;
}