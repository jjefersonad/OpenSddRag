import { useEffect, useState } from "react";
import { getTree, type TreeData, type TreeNode } from "../../api/tree";

/**
 * Hierarchy tab (REQ-016): the active change's artifact chain as a vertical
 * timeline — proposal → specs → design/tasks → tests. Visual grammar from
 * the prototype (docs/ui/OpenSddRag.dc.html): 13px dots + 2px connector
 * lines (done #10b981 / active #34d399 with glow / pending #2b3238),
 * type chips in mono 10px (proposal amber #fbbf24, spec blue #60a5fa,
 * design violet #a78bfa, task green #34d399, test gray #8a9298), caret
 * expand (▶ rotates 90°), cards #131619 with hairline borders.
 */

const TYPE_CHIP: Record<string, { color: string; bg: string; label: string }> = {
  proposal: { color: "#fbbf24", bg: "rgba(251,191,36,0.12)", label: "proposal" },
  spec: { color: "#60a5fa", bg: "rgba(96,165,250,0.12)", label: "spec" },
  design: { color: "#a78bfa", bg: "rgba(167,139,250,0.12)", label: "design" },
  task: { color: "#34d399", bg: "rgba(52,211,153,0.12)", label: "task" },
  test: { color: "#8a9298", bg: "rgba(255,255,255,0.06)", label: "test" },
};

const STATUS_DOT: Record<string, string> = {
  archived: "#10b981", // done
  active: "#34d399", // in progress
  draft: "#2b3238", // pending
};
const STATUS_LABEL: Record<string, string> = {
  archived: "done",
  active: "in progress",
  draft: "pending",
  passing: "passing",
  failing: "failing",
};
/** test artifacts carry test_status, not lifecycle status */
function statusOf(node: TreeNode): string {
  if (node.type === "test") {
    return node.status === "passing" ? "passing" : "draft";
  }
  return node.status;
}

export interface ParsedNode {
  node: TreeNode;
  children: ParsedNode[];
}

/** Build the parent→children structure from the flat nodes+edges (design D3:
 *  edges define links; depth order provides the fallback). */
export function parseTree(tree: TreeData): { roots: ParsedNode[]; byId: Map<string, ParsedNode> } {
  const byId = new Map<string, ParsedNode>();
  const outNodes: ParsedNode[] = [];
  for (const flow of tree.flows) {
    for (const node of [...flow.nodes].sort((a, b) => a.depth - b.depth)) {
      const entry: ParsedNode = { node, children: [] };
      byId.set(node.id, entry);
      outNodes.push(entry);
    }
  }
  const parentOf = new Map<string, string>();
  for (const flow of tree.flows) {
    for (const edge of flow.edges) {
      // child := edge.source; parent := edge.target (source implements target)
      if (byId.has(edge.source) && byId.has(edge.target)) {
        parentOf.set(edge.source, edge.target);
      }
    }
  }
  const roots: ParsedNode[] = [];
  for (const entry of outNodes) {
    const parentId = parentOf.get(entry.node.id);
    if (parentId && parentId !== entry.node.id) {
      byId.get(parentId)!.children.push(entry);
    } else {
      roots.push(entry);
    }
  }
  // sort children by depth then name
  const sortRec = (list: ParsedNode[]) => {
    list.sort((a, b) => a.node.depth - b.node.depth || a.node.name.localeCompare(b.node.name));
    list.forEach((c) => sortRec(c.children));
  };
  sortRec(roots);
  return { roots, byId };
}

/** One node row: dot + connector line + chip + name + status + caret. */
export function TreeNodeView({
  node,
  children: childComponents,
  onNavigate,
  childrenCount,
  onToggle,
  expanded,
  isRoot,
}: {
  node: TreeNode;
  children: React.ReactNode[];
  onNavigate: (node: TreeNode) => void;
  childrenCount?: number;
  onToggle?: () => void;
  expanded?: boolean;
  isRoot?: boolean;
}) {
  const chip = TYPE_CHIP[node.type] ?? TYPE_CHIP.test;
  const status = statusOf(node);
  const dotColor = STATUS_DOT[status] ?? "#2b3238";
  const isExpandedLike = isRoot || expanded;

  return (
    <div data-testid={`tree-node-${node.id}`} style={{ display: "flex", gap: 14, position: "relative", paddingBottom: 16 }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", position: "relative" }}>
        <div
          style={{
            width: 13,
            height: 13,
            borderRadius: 99,
            background: dotColor,
            border: "2px solid #0a0c0d",
            zIndex: 2,
            boxShadow: status === "active" ? "0 0 0 4px rgba(52,211,153,0.18)" : undefined,
            flexShrink: 0,
          }}
        />
        {childComponents.length > 0 ? (
          <div style={{ flex: 1, width: 2, background: status === "draft" ? "rgba(255,255,255,0.1)" : dotColor, marginTop: 2 }} />
        ) : null}
      </div>
      <div style={{ flex: 1, minWidth: 0, paddingTop: -2, cursor: "pointer" }} onClick={() => onNavigate(node)}>
        <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap" }}>
          {childComponents.length > 0 ? (
            <span
              data-testid={`tree-caret-${node.id}`}
              onClick={(e) => {
                e.stopPropagation();
                onToggle?.();
              }}
              style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#5b6469", transform: isExpandedLike ? "rotate(90deg)" : "none", transition: "transform .15s", cursor: "pointer" }}
            >
              ▶
            </span>
          ) : null}
          <span data-testid={`type-chip-${node.type}`} style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: chip.color, background: chip.bg, borderRadius: 5, padding: "3px 8px", whiteSpace: "nowrap" }}>
            {chip.label}
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 13.5, color: "#e8ebed", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {node.name}
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: dotColor }}>{STATUS_LABEL[status] ?? status}</span>
          {typeof childrenCount === "number" && childrenCount > 0 ? (
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "#6b747a", background: "rgba(255,255,255,0.06)", borderRadius: 5, padding: "1px 6px" }}>{childrenCount}</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function NodeBranch({
  parsed,
  onNavigate,
  expandedSet,
  defaultExpand,
}: {
  parsed: ParsedNode;
  onNavigate: (node: TreeNode) => void;
  expandedSet: Set<string>;
  defaultExpand: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpand);
  const hasChildren = parsed.children.length > 0;
  const isOpen = expandedSet.has(parsed.node.id) ?? expanded;
  useEffect(() => {
    if (expandedSet.has(parsed.node.id)) setExpanded(true);
  }, [expandedSet, parsed.node.id]);

  return (
    <div>
      <TreeNodeView
        node={parsed.node}
        children={[]}
        onNavigate={onNavigate}
        childrenCount={parsed.children.length}
        onToggle={() => hasChildren && setExpanded((v) => !v)}
        expanded={isOpen}
      />
      {isOpen && hasChildren ? (
        <div style={{ paddingLeft: 24, marginLeft: 5, borderLeft: "2px solid rgba(255,255,255,0.05)" }}>
          {parsed.children.map((child) => (
            <NodeBranch key={child.node.id} parsed={child} onNavigate={onNavigate} expandedSet={expandedSet} defaultExpand={child.node.depth <= 1} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** Hierarchy tab body: fetches the tree and renders per-flow timelines. */
export default function HierarchyTab({ slug, onNavigate }: { slug: string; onNavigate?: (type: string) => void }) {
  const [tree, setTree] = useState<TreeData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const expandedSet = new Set<string>();

  useEffect(() => {
    let alive = true;
    setError(null);
    getTree(slug)
      .then((t) => alive && setTree(t))
      .catch((err: unknown) => alive && setError(err instanceof Error ? err.message : "failed to load tree"));
    return () => {
      alive = false;
    };
  }, [slug]);

  if (error) return <p role="alert">{error}</p>;
  if (!tree) return <p>Loading…</p>;
  if (!tree.change) {
    return (
      <div
        data-testid="hierarchy-empty"
        style={{ textAlign: "center", padding: 50, color: "#6b747a", fontSize: 14, border: "1px dashed rgba(255,255,255,0.1)", borderRadius: 12 }}
      >
        No active change — run <span style={{ fontFamily: "var(--font-mono)", color: "#34d399" }}>/opsr:propose</span> to start one.
      </div>
    );
  }

  const navigate = (node: TreeNode) => {
    onNavigate?.(node.type);
  };

  return (
    <div data-testid="hierarchy-tree" style={{ maxWidth: 820 }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "#6b747a", marginBottom: 18 }}>
        change: <span style={{ color: "#34d399" }}>{tree.change}</span>
      </div>
      {tree.flows.map((flow) => (
        <div key={flow.flow} style={{ marginBottom: 24 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.09em", textTransform: "uppercase", color: "#5b6469", marginBottom: 12 }}>
            {flow.flow}
          </div>
          <div style={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 18 }}>
            {parseTree(flow.edges ? { ...tree, flows: [flow] } : tree).roots.length > 0
              ? (function render() {
                  const { roots } = parseTree({ change: tree.change, flows: [flow] });
                  return roots.map((root) => (
                    <NodeBranch key={root.node.id} parsed={root} onNavigate={navigate} expandedSet={expandedSet} defaultExpand={true} />
                  ));
                })()
              : null}
          </div>
        </div>
      ))}
    </div>
  );
}