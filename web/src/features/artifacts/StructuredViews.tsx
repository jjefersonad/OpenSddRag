import type { Artifact } from "../../api/types";
import { parseSections, parseDesignSections } from "./parsers";

/** Structured proposal renderer (REQ-015): Problem / What changes /
 *  Affected capabilities / Out of scope — tolerant fallback to raw. */
export function ProposalView({ artifact }: { artifact: Artifact }) {
  const content = artifact.content ?? "";
  const sections = parseSections(content, [
    "Why",
    "What Changes",
    "Out of Scope",
    "Impact",
  ]);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      <Section title="Problem (Why)" body={sections["Why"]} />
      <Section title="What changes" body={sections["What Changes"]} />
      <Section title="Affected capabilities" body={capabilitiesBody(content)} />
      <Section title="Impact" body={sections["Impact"]} />
      <Section title="Out of scope" body={sections["Out of Scope"]} />
    </div>
  );
}

function capabilitiesBody(content: string): string {
  const caps = parseSections(content, ["Capabilities"]);
  return caps["Capabilities"] || "";
}

function Section({ title, body }: { title: string; body: string }) {
  if (!body) return null;
  return (
    <div>
      <div className="label" style={{ marginBottom: "6px" }}>{title}</div>
      <pre style={{ margin: 0, whiteSpace: "pre-wrap", color: "var(--color-text-secondary)", fontSize: "13px", fontFamily: "inherit" }}>
        {body}
      </pre>
    </div>
  );
}

/** Structured design renderer (REQ-015): Technical decisions / Trade-offs /
 *  Risks. */
export function DesignView({ artifact }: { artifact: Artifact }) {
  const parsed = parseDesignSections(artifact.content ?? "");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      <div>
        <div className="label" style={{ marginBottom: "6px" }}>Technical decisions</div>
        {parsed.decisions.length === 0 ? (
          <p style={{ margin: 0, color: "var(--color-text-tertiary)", fontSize: "13px" }}>None recorded.</p>
        ) : (
          <ul style={{ margin: 0, paddingLeft: "18px" }}>
            {parsed.decisions.map((decision, i) => (
              <li key={i} style={{ color: "var(--color-text-secondary)", fontSize: "13px" }}>{decision}</li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <div className="label" style={{ marginBottom: "6px" }}>Trade-offs &amp; risks</div>
        {parsed.risks.length === 0 ? (
          <p style={{ margin: 0, color: "var(--color-text-tertiary)", fontSize: "13px" }}>None recorded.</p>
        ) : (
          <ul style={{ margin: 0, paddingLeft: "18px" }}>
            {parsed.risks.map((risk, i) => (
              <li key={i} style={{ color: "var(--color-text-secondary)", fontSize: "13px" }}>{risk}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}