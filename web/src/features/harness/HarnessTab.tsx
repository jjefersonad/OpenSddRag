import { useRules } from "../../hooks/useRules";
import RuleRow from "./RuleRow";

/** Harness tab: one row per rule with badges + optimistic toggle. */
export default function HarnessTab({ slug }: { slug: string }) {
  const { rules, loading, error } = useRules(slug);

  if (loading) return <p>Loading…</p>;
  if (error) return <p role="alert">{error}</p>;
  if (rules.length === 0) return <p>No harness rules.</p>;

  return (
    <div role="table" aria-label="Harness rules">
      {rules.map((rule) => (
        <RuleRow key={rule.id} slug={slug} rule={rule} />
      ))}
    </div>
  );
}
