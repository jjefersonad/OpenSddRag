import { useArtifacts } from "../../hooks/useArtifacts";
import ArtifactCard from "./ArtifactCard";
import SpecCard from "./SpecCard";

/** Renders a project's artifacts for one tab (filtered by type). Specs use the
 *  expandable SpecCard; other types use the compact ArtifactCard. */
export default function ArtifactsTab({
  slug,
  type,
}: {
  slug: string;
  type?: string;
}) {
  const { artifacts, loading, error } = useArtifacts(slug, type);

  if (loading) return <p>Loading…</p>;
  if (error) return <p role="alert">{error}</p>;
  if (artifacts.length === 0) return <p>Nothing here yet.</p>;

  return (
    <div>
      {artifacts.map((artifact) =>
        artifact.type === "spec" ? (
          <SpecCard key={artifact.id} artifact={artifact} />
        ) : (
          <ArtifactCard key={artifact.id} artifact={artifact} />
        ),
      )}
    </div>
  );
}
