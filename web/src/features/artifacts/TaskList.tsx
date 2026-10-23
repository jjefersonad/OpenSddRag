import { useArtifacts } from "../../hooks/useArtifacts";
import TaskRow from "./TaskRow";

/** Tasks tab: task artifacts rendered as optimistic checkboxes. */
export default function TaskList({ slug }: { slug: string }) {
  const { artifacts, loading, error } = useArtifacts(slug, "task", undefined, true);

  if (loading) return <p>Loading…</p>;
  if (error) return <p role="alert">{error}</p>;
  if (artifacts.length === 0) return <p>No tasks yet.</p>;

  return (
    <div>
      {artifacts.map((task) => (
        <TaskRow key={task.id} slug={slug} task={task} />
      ))}
    </div>
  );
}
