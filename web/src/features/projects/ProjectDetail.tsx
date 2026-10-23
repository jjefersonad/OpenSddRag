import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProject } from "../../api/projects";
import { listFlows } from "../../api/flows";
import { getChanges, type ChangeSummary } from "../../api/changes";
import type { FlowInfo, ProjectDetailData } from "../../api/types";
import TabBar, { type TabBarTab } from "../../components/ui/TabBar";
import ArtifactsTab from "../artifacts/ArtifactsTab";
import TaskList from "../artifacts/TaskList";
import HarnessTab from "../harness/HarnessTab";
import OverviewTab from "./OverviewTab";
import HierarchyTab from "../hierarchy/HierarchyTab";
import FlowPhaseStrip from "./FlowPhaseStrip";
import ChangeReader from "../changes/ChangeReader";

/**
 * Project detail shell (REQ-014/REQ-020, design D7): header (name, stage chip
 * of the active change, `change: <name> · <language>` line), the horizontal
 * FlowPhaseStrip of the active change's phases (omitted without a lifecycle),
 * and the TabBar with order Overview → one per registered kind → Hierarchy →
 * Harness. `getChanges` is fetched once here and shared with the Overview;
 * the breadcrumb lives in the app shell only (REQ-014 single breadcrumb).
 */
export default function ProjectDetail() {
  const { slug, change } = useParams();
  const [project, setProject] = useState<ProjectDetailData | null>(null);
  const [flows, setFlows] = useState<FlowInfo[]>([]);
  const [changes, setChanges] = useState<ChangeSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    let active = true;
    if (!slug) return;
    setProject(null);
    setChanges(null);
    setError(null);
    getProject(slug)
      .then((data) => {
        if (active) setProject(data);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "failed to load project");
      });
    listFlows().then((f) => active && setFlows(f), () => active && setFlows([]));
    getChanges(slug).then((c) => active && setChanges(c), () => active && setChanges([]));
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

  const activeChange = changes?.[0] ?? null;
  const stripPhases = activeChange ? headerStripPhases(activeChange, flows) : null;

  const tabBarTabs: TabBarTab[] = tabs.map((entry) => ({
    key: entry.key,
    label: entry.label,
    count: entry.type ? project.summary?.[entry.type] : undefined,
  }));

  return (
    <section>
      <header style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px" }}>
          <h1 data-testid="app-h1" style={{ margin: 0, fontSize: "25px", fontWeight: 700, letterSpacing: "-0.02em" }}>
            {project.name ?? project.slug}
          </h1>
          {activeChange ? (
            <span
              data-testid="detail-stage-chip"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                padding: "4px 9px",
                borderRadius: "6px",
                color: "var(--color-accent-hover)",
                background: "rgba(16,185,129,0.1)",
                border: "1px solid rgba(16,185,129,0.25)",
              }}
            >
              {activeChangePhaseName(activeChange)}
            </span>
          ) : null}
        </div>
        {activeChange ? (
          <div
            data-testid="header-change-line"
            style={{ fontFamily: "var(--font-mono)", fontSize: "12.5px", color: "var(--color-text-tertiary)" }}
          >
            change: <span style={{ color: "var(--color-accent-hover)" }}>{activeChange.change}</span>
            {project.language ? <> · {project.language}</> : null}
          </div>
        ) : null}
      </header>

      {activeChange && stripPhases ? <FlowPhaseStrip flow={activeChange.flow} phases={stripPhases} /> : null}

      {change ? (
        <>
          <p style={{ margin: "0 0 18px" }}>
            <Link
              to={`/p/${slug}`}
              data-testid="reader-back-overview"
              style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--color-accent-hover)", textDecoration: "none" }}
            >
              ← Overview
            </Link>
          </p>
          <ChangeReader slug={slug ?? ""} change={change} />
        </>
      ) : (
        <>
          <TabBar tabs={tabBarTabs} active={tab} onSelect={setTab} />
          <div role="tabpanel">
            {renderTabContent(slug ?? "", tab, flows, changes, (nodeType: string) => {
              const target = buildTabs(project, flows).find((t) => t.type === nodeType && nodeType !== "test");
              setTab(target?.key ?? (nodeType === "test" ? "task" : "overview"));
            })}
          </div>
        </>
      )}
    </section>
  );
}

/** The change's phases for the header strip; null when its flow declares no
 *  lifecycle (REQ-014 "Flow without lifecycle"). */
function headerStripPhases(change: ChangeSummary, flows: FlowInfo[]) {
  const flow = flows.find((f) => f.flow === change.flow);
  if (!flow || !flow.lifecycle?.length || change.phases.length === 0) return null;
  return change.phases;
}

/** The currently reached phase of the change — the one with status "active",
 *  falling back to the last phase when every phase is done. */
function activeChangePhaseName(change: ChangeSummary): string | null {
  const active = change.phases.find((p) => p.status === "active");
  return active?.name ?? change.phases.at(-1)?.name ?? null;
}

interface TabEntry {
  key: string;
  label: string;
  type?: string;
  flow?: string;
}

function buildTabs(project: ProjectDetailData | null, flows: FlowInfo[]): TabEntry[] {
  const tabs: TabEntry[] = [{ key: "overview", label: "Overview" }];
  const seen = new Set<string>();
  for (const flow of flows) {
    for (const kindEntry of flow.kinds) {
      const kind = kindEntry.kind;
      if (seen.has(kind)) continue;
      seen.add(kind);
      if (kind === "task") {
        tabs.push({ key: "task", label: labelFor(kind), type: kind });
      } else {
        tabs.push({ key: kind, label: labelFor(kind), type: kind });
      }
    }
  }
  tabs.push({ key: "hierarchy", label: "Hierarchy" });
  tabs.push({ key: "harness", label: "Harness" });
  return tabs;
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
  slug: string,
  tab: string,
  flows: FlowInfo[],
  changes: ChangeSummary[] | null,
  onNavigate: (nodeType: string) => void,
) {
  switch (tab) {
    case "overview":
      return <OverviewTab slug={slug} changes={changes} />;
    case "hierarchy":
      return <HierarchyTab slug={slug} onNavigate={onNavigate} />;
    case "harness":
      return <HarnessTab slug={slug} />;
    default: {
      const entry = buildTabs(null, flows).find((t) => t.key === tab);
      const type = entry?.type ?? tab;
      if (type === "task") return <TaskList slug={slug} />;
      return <ArtifactsTab slug={slug} type={type} flow={entry?.flow} />;
    }
  }
}