import { useArtifacts } from "../../hooks/useArtifacts";
import ArtifactCard from "./ArtifactCard";
import GenericArtifactView from "./GenericArtifactView";
import SpecCard from "./SpecCard";
import { DesignView, ProposalView } from "./StructuredViews";
import { hasStructuredRenderer } from "./parsers";

/**
 * Renders a project's artifacts for one tab (filtered by type + flow,
 * web-api delta REQ-009). Dispatch (design D7): spec → full spec cards
 * (REQ-015); proposal/design → structured views; unknown kinds →
 * generic metadata+raw renderer.
 */
export default function ArtifactsTab({
  slug,
  type,
  flow,
}: {
  slug: string;
  type?: string;
  flow?: string;
}) {
  // Structured SDD kinds need the body: request include=content in the
  // single list request (REQ-015) — no per-artifact getArtifact.
  const includeContent = type === "spec" || type === "proposal" || type === "design";
  const { artifacts, loading, error } = useArtifacts(slug, type, flow, includeContent);

  if (loading) return <p>Loading…</p>;
  if (error) return <p role="alert">{error}</p>;
  if (artifacts.length === 0) return <p>Nothing here yet.</p>;

  const visible = flow ? artifacts.filter((a) => (a.flow ?? "sdd") === flow) : artifacts;

  return (
    <div>
      {visible.map((artifact) => {
        const kind = artifact.type;
        if (kind === "spec") return <SpecCard key={artifact.id} artifact={artifact} />;
        if (kind === "proposal") return <ProposalView key={artifact.id} artifact={artifact} />;
        if (kind === "design") return <DesignView key={artifact.id} artifact={artifact} />;
        if (hasStructuredRenderer(kind)) return <ArtifactCard key={artifact.id} artifact={artifact} />;
        return <GenericArtifactView key={artifact.id} artifact={artifact} />;
      })}
    </div>
  );
}