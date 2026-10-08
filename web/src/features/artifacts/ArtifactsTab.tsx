import { useArtifacts } from "../../hooks/useArtifacts";
import ArtifactCard from "./ArtifactCard";
import GenericArtifactView from "./GenericArtifactView";
import SpecRequirementList from "./SpecRequirementList";
import { DesignView, ProposalView } from "./StructuredViews";
import { hasStructuredRenderer } from "./parsers";

/**
 * Renders a project's artifacts for one tab (filtered by type + flow,
 * web-api delta REQ-009). Dispatch (design D7): spec → structured
 * requirements list; proposal/design → structured views; unknown kinds →
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
  const { artifacts, loading, error } = useArtifacts(slug, type);

  if (loading) return <p>Loading…</p>;
  if (error) return <p role="alert">{error}</p>;
  if (artifacts.length === 0) return <p>Nothing here yet.</p>;

  const visible = flow ? artifacts.filter((a) => (a.flow ?? "sdd") === flow) : artifacts;

  return (
    <div>
      {visible.map((artifact) => {
        const kind = artifact.type;
        if (kind === "spec") return <SpecRequirementList key={artifact.id} artifact={artifact} />;
        if (kind === "proposal") return <ProposalView key={artifact.id} artifact={artifact} />;
        if (kind === "design") return <DesignView key={artifact.id} artifact={artifact} />;
        if (hasStructuredRenderer(kind)) return <ArtifactCard key={artifact.id} artifact={artifact} />;
        return <GenericArtifactView key={artifact.id} artifact={artifact} />;
      })}
    </div>
  );
}