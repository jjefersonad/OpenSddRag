import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../../api/client";
import { deleteProject, getProject } from "../../api/projects";
import ConfirmDialog from "../../components/ConfirmDialog";
import CreateProjectModal from "./CreateProjectModal";
import { listFlows } from "../../api/flows";
import { CHANGES_PAGE_SIZE, getChanges, type ChangeSummary } from "../../api/changes";
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
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectDetailData | null>(null);
  const [flows, setFlows] = useState<FlowInfo[]>([]);
  const [changes, setChanges] = useState<ChangeSummary[] | null>(null);
  const [changesTotal, setChangesTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSlug, setPageSlug] = useState(slug);
  const [revision, setRevision] = useState(0);
  if (slug !== pageSlug) {
    setPageSlug(slug);
    setPage(1);
    setProject(null);
    setChanges(null);
    setRevision(0);
  }
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState("overview");
  const [stage, setStage] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let active = true;
    if (!slug) return;
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
  }, [slug, revision]);

  useEffect(() => {
    let active = true;
    if (!slug) return;
    getChanges(slug, page, CHANGES_PAGE_SIZE).then(
      (data) => {
        if (!active) return;
        setChanges(data.items);
        setChangesTotal(data.total);
      },
      () => {
        if (!active) return;
        setChanges([]);
        setChangesTotal(0);
      },
    );
    return () => {
      active = false;
    };
  }, [slug, page, revision]);

  useEffect(() => {
    setStage(null);
  }, [slug, change]);

  const tabs = useMemo(
    () => buildTabs(project, flows),
    [project, flows],
  );

  if (error) return <p role="alert">{error}</p>;
  if (!project) return <p>Loading…</p>;

  const headerChange = change
    ? (changes?.find((entry) => entry.change === change) ?? null)
    : (changes?.[0] ?? null);
  const stripPhases = headerChange ? headerStripPhases(headerChange, flows) : null;
  const stageKinds = stage
    ? (flows.find((flow) => flow.flow === headerChange?.flow)?.lifecycle?.find((phase) => phase.name === stage)?.kinds ?? [])
    : null;

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
          {headerChange ? (
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
              {activeChangePhaseName(headerChange)}
            </span>
          ) : null}
          <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <button type="button" onClick={() => setEditing(true)} style={HEADER_ACTION}>
              Edit
            </button>
            <button
              type="button"
              onClick={() => {
                setDeleteError(null);
                setConfirmingDelete(true);
              }}
              style={{ ...HEADER_ACTION, color: "var(--color-danger)" }}
            >
              Delete
            </button>
          </div>
        </div>
        {headerChange ? (
          <div
            data-testid="header-change-line"
            style={{ fontFamily: "var(--font-mono)", fontSize: "12.5px", color: "var(--color-text-tertiary)" }}
          >
            change: <span style={{ color: "var(--color-accent-hover)" }}>{headerChange.change}</span>
            {project.language ? <> · {project.language}</> : null}
          </div>
        ) : null}
      </header>

      {headerChange && stripPhases ? (
        <FlowPhaseStrip
          flow={headerChange.flow}
          phases={stripPhases}
          selected={stage}
          onSelect={change ? (name) => setStage((current) => (current === name ? null : name)) : undefined}
        />
      ) : null}

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
          <ChangeReader
            slug={slug ?? ""}
            change={change}
            summary={headerChange}
            stageKinds={stageKinds}
            onChanged={() => setRevision((value) => value + 1)}
          />
        </>
      ) : (
        <>
          <TabBar tabs={tabBarTabs} active={tab} onSelect={setTab} />
          <div role="tabpanel">
            {renderTabContent(slug ?? "", tab, flows, changes, changesTotal, page, setPage, () => setRevision((value) => value + 1), (nodeType: string) => {
              const target = buildTabs(project, flows).find((t) => t.type === nodeType && nodeType !== "test");
              setTab(target?.key ?? (nodeType === "test" ? "task" : "overview"));
            })}
          </div>
        </>
      )}
      {editing && project ? (
        <CreateProjectModal
          project={project}
          onClose={() => setEditing(false)}
          onChanged={(nextSlug) => {
            setEditing(false);
            if (nextSlug && nextSlug !== slug) navigate(`/p/${nextSlug}`);
            else setRevision((value) => value + 1);
          }}
        />
      ) : null}
      {confirmingDelete && project ? (
        <ConfirmDialog
          title="Delete project"
          message={`Delete ${project.name ?? project.slug} and every artifact in it? This cannot be undone.`}
          confirmLabel="Delete"
          busy={deleting}
          error={deleteError}
          onClose={() => setConfirmingDelete(false)}
          onConfirm={async () => {
            setDeleting(true);
            setDeleteError(null);
            try {
              await deleteProject(project.slug);
              navigate("/projects", {
                state: { notice: `Project ${project.name ?? project.slug} was deleted.` },
              });
            } catch (err) {
              setDeleteError(err instanceof ApiError ? err.message : "Could not reach the API.");
              setDeleting(false);
            }
          }}
        />
      ) : null}
    </section>
  );
}

const HEADER_ACTION = {
  background: "transparent",
  border: "1px solid var(--color-border)",
  borderRadius: "6px",
  color: "var(--color-text-secondary)",
  fontSize: "12px",
  padding: "4px 8px",
  cursor: "pointer",
} as const;

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
  changesTotal: number,
  page: number,
  onPage: (page: number) => void,
  onChanged: () => void,
  onNavigate: (nodeType: string) => void,
) {
  switch (tab) {
    case "overview":
      return (
        <OverviewTab
          slug={slug}
          changes={changes}
          total={changesTotal}
          page={page}
          pageSize={CHANGES_PAGE_SIZE}
          onPage={onPage}
        />
      );
    case "hierarchy":
      return <HierarchyTab slug={slug} onNavigate={onNavigate} />;
    case "harness":
      return <HarnessTab slug={slug} />;
    default: {
      const entry = buildTabs(null, flows).find((t) => t.key === tab);
      const type = entry?.type ?? tab;
      if (type === "task") return <TaskList slug={slug} onChanged={onChanged} />;
      return <ArtifactsTab slug={slug} type={type} flow={entry?.flow} onChanged={onChanged} />;
    }
  }
}