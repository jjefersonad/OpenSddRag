import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { getChangeBundle, type ChangeBundle, type ChangeTask } from "../../api/changes";
import type { Artifact } from "../../api/types";
import { DesignView, ProposalView } from "../artifacts/StructuredViews";
import SpecCard from "../artifacts/SpecCard";
import TaskRow from "../artifacts/TaskRow";
import { displayTitle } from "../artifacts/parsers";

const SECTION_LABEL = {
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  letterSpacing: "0.09em",
  textTransform: "uppercase" as const,
  color: "#5b6469",
  marginBottom: 14,
};

function taskAsArtifact(task: ChangeTask, change: string): Artifact {
  return {
    id: task.name,
    name: task.name,
    type: "task",
    status: task.status,
    content: task.content,
    metadata: { done: task.done, change_name: change },
  };
}

/** One-change document: proposal → specs → design → tasks (design D5). */
export default function ChangeReader({ slug, change }: { slug: string; change: string }) {
  const [bundle, setBundle] = useState<ChangeBundle | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setBundle(null);
    setError(null);
    getChangeBundle(slug, change)
      .then((data) => {
        if (alive) setBundle(data);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        if (err instanceof ApiError && err.code === "NOT_FOUND") {
          setError("Change not found.");
        } else {
          setError(err instanceof Error ? err.message : "failed to load change");
        }
      });
    return () => {
      alive = false;
    };
  }, [slug, change]);

  if (error) return <p role="alert">{error}</p>;
  if (!bundle) return <p>Loading…</p>;

  return (
    <article data-testid="change-reader" style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      <section>
        <div style={SECTION_LABEL}>Proposal</div>
        {bundle.proposal ? (
          <>
            <h2 style={{ margin: "0 0 12px", fontSize: 20, fontWeight: 650 }}>
              {displayTitle({
                type: "proposal",
                name: bundle.proposal.name,
                content: bundle.proposal.content,
                changeName: change,
              })}
            </h2>
            <ProposalView artifact={bundle.proposal} />
          </>
        ) : (
          <p style={{ color: "var(--color-text-tertiary)", fontSize: 13 }}>No proposal yet</p>
        )}
      </section>

      <section>
        <div style={SECTION_LABEL}>Specs</div>
        {bundle.specs.length === 0 ? (
          <p style={{ color: "var(--color-text-tertiary)", fontSize: 13 }}>No specs yet</p>
        ) : (
          bundle.specs.map((spec) => (
            <SpecCard
              key={spec.id ?? spec.name}
              artifact={spec}
              title={displayTitle({
                type: "spec",
                name: spec.name,
                content: spec.content,
                changeName: change,
              })}
            />
          ))
        )}
      </section>

      <section>
        <div style={SECTION_LABEL}>Design</div>
        {bundle.design ? (
          <>
            <h2 style={{ margin: "0 0 12px", fontSize: 20, fontWeight: 650 }}>
              {displayTitle({
                type: "design",
                name: bundle.design.name,
                content: bundle.design.content,
                changeName: change,
              })}
            </h2>
            <DesignView artifact={bundle.design} />
          </>
        ) : (
          <p style={{ color: "var(--color-text-tertiary)", fontSize: 13 }}>No design yet</p>
        )}
      </section>

      <section>
        <div style={SECTION_LABEL}>Tasks</div>
        {bundle.tasks.length === 0 ? (
          <p style={{ color: "var(--color-text-tertiary)", fontSize: 13 }}>No tasks yet</p>
        ) : (
          bundle.tasks.map((task) => (
            <TaskRow key={task.name} slug={slug} task={taskAsArtifact(task, change)} readOnly />
          ))
        )}
      </section>
    </article>
  );
}
