import { Link } from "react-router-dom";
import PublicNav from "../../components/PublicNav";

/**
 * Public landing page (REQ-011) — faithful to docs/ui/AGENT_GUIDE.md and
 * the prototype `OpenSddRag.dc.html`: top nav, hero + terminal demo, the
 * artifact lifecycle pipeline, and the three memory layers. Visual tokens
 * §8 via CSS variables (inline styles per design D5).
 */

const FLOW_STEPS = ["Propose", "Spec", "Design", "Tasks", "Apply", "Verify", "Sync", "Archive"];

const MEMORY_LAYERS = [
  {
    tag: "artifacts · vector(384)",
    title: "Semantic memory",
    desc: "Proposals, specs, designs and tasks — each embedded and searchable by meaning, not keywords.",
    meta: "HNSW · vector_cosine_ops",
  },
  {
    tag: "execution_traces",
    title: "Episodic memory",
    desc: "An embedded log of every agent action, so past decisions can be recalled in future sessions.",
    meta: "all-MiniLM-L6-v2",
  },
  {
    tag: "sessions · project_rules",
    title: "Working context + harness",
    desc: "Active artifact ids plus behavioral rules injected into every session — surviving context resets.",
    meta: "always · on_apply · on_verify",
  },
];

const TERMINAL_LINES: { prompt?: string; out?: string }[] = [
  { prompt: "/opsr:propose add-stripe-billing" },
  { out: "✓ proposal.md created · 3 capabilities affected" },
  { prompt: "/opsr:spec" },
  { out: "✓ billing · webhooks specs generated" },
  { prompt: "/opsr:design && /opsr:tasks" },
  { out: "✓ design.md · 8 tasks across 3 groups" },
  { prompt: "/opsr:apply" },
  { out: "[x] stripe client wrapper" },
  { out: "[x] webhook signature verify" },
  { out: "[ ] idempotent event processor" },
];

export default function LandingPage() {
  return (
    <div
      style={{
        position: "relative",
        overflow: "hidden",
        minHeight: "100%",
        background: "var(--color-page)",
        color: "var(--color-text-primary)",
      }}
    >
      {/* decorative layers (REQ-018): never intercept clicks, never hide content */}
      <div
        data-testid="landing-grid-bg"
        aria-hidden="true"
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.025) 1px,transparent 1px)",
          backgroundSize: "44px 44px",
          animation: "gridmove 18s linear infinite",
          maskImage: "radial-gradient(ellipse 80% 60% at 50% 0%,#000 30%,transparent 75%)",
          WebkitMaskImage: "radial-gradient(ellipse 80% 60% at 50% 0%,#000 30%,transparent 75%)",
        }}
      />
      <div
        data-testid="landing-glow"
        aria-hidden="true"
        style={{
          position: "absolute",
          top: "-180px",
          left: "50%",
          transform: "translateX(-50%)",
          width: "760px",
          height: "420px",
          pointerEvents: "none",
          background: "radial-gradient(ellipse,rgba(16,185,129,0.14),transparent 68%)",
        }}
      />
      <div style={{ position: "relative", zIndex: 1 }}>
      <PublicNav />

      {/* hero + terminal */}
      <section
        data-testid="landing-hero"
        style={{
          maxWidth: "1180px",
          margin: "0 auto",
          padding: "64px 32px 40px",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "56px",
          alignItems: "center",
        }}
      >
        <div>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              fontFamily: "var(--font-mono)",
              fontSize: "12px",
              color: "#34d399",
              background: "rgba(16,185,129,0.1)",
              border: "1px solid rgba(16,185,129,0.25)",
              padding: "6px 12px",
              borderRadius: "99px",
              marginBottom: "24px",
            }}
          >
            Spec-Driven Development + Harness
          </div>
          <h1 style={{ fontSize: "50px", lineHeight: 1.04, letterSpacing: "-0.03em", margin: "0 0 20px", fontWeight: 700 }}>
            Give your AI agent
            <br />
            <span style={{ color: "#34d399" }}>persistent memory</span>
            <br />
            and a disciplined workflow.
          </h1>
          <p style={{ fontSize: "17px", lineHeight: 1.6, color: "#9aa2a8", margin: "0 0 30px", maxWidth: "440px" }}>
            An MCP server with semantic memory and a structured pipeline. Every change flows
            through well-defined phases instead of ad-hoc edits — proposal, spec, design, tasks,
            apply, verify, archive.
          </p>
          <div style={{ display: "flex", gap: "13px", alignItems: "center" }}>
            <Link
              to="/login"
              data-testid="landing-launch"
              style={{
                background: "var(--color-accent)",
                color: "var(--color-on-accent)",
                padding: "13px 24px",
                borderRadius: "9px",
                fontWeight: 600,
                fontSize: "15px",
              }}
            >
              Open the dashboard
            </Link>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "13px", color: "#6b747a" }}>
              <span style={{ color: "#34d399" }}>$</span> opensddrag init
            </div>
          </div>
        </div>

        {/* terminal demo */}
        <div
          data-testid="landing-terminal"
          style={{
            background: "var(--color-inset)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "13px",
            overflow: "hidden",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "7px", padding: "12px 15px", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
            <span style={{ width: 11, height: 11, borderRadius: 99, background: "#ff5f57" }} />
            <span style={{ width: 11, height: 11, borderRadius: 99, background: "#febc2e" }} />
            <span style={{ width: 11, height: 11, borderRadius: 99, background: "#28c840" }} />
            <span style={{ marginLeft: 8, fontFamily: "var(--font-mono)", fontSize: 11, color: "#5b6469" }}>
              claude-code — opensddrag
            </span>
          </div>
          <div style={{ padding: "18px", fontFamily: "var(--font-mono)", fontSize: "12.5px", lineHeight: 1.85 }}>
            {TERMINAL_LINES.map((line, i) =>
              line.prompt ? (
                <div key={i} style={{ color: "#6b747a", marginTop: i > 0 ? 6 : 0 }}>
                  <span style={{ color: "#34d399" }}>➜</span> {line.prompt}
                </div>
              ) : (
                <div key={i} style={{ color: "#9aa2a8", paddingLeft: 14 }}>
                  {line.out}
                </div>
              ),
            )}
            <div style={{ marginTop: 10, color: "#5b6469" }}>
              ↳ harness: <span style={{ color: "#fbbf24" }}>webhook-idempotency</span> rule active
            </div>
          </div>
        </div>
      </section>

      {/* artifact lifecycle pipeline */}
      <section style={{ maxWidth: "1180px", margin: "0 auto", padding: "30px 32px 18px" }}>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "#5b6469",
            marginBottom: 16,
          }}
        >
          The artifact lifecycle
        </div>
        <div
          data-testid="landing-pipeline"
          style={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            background: "var(--color-inset)",
            border: "1px solid var(--color-border)",
            borderRadius: "12px",
            padding: "22px 20px",
          }}
        >
          {FLOW_STEPS.map((label, i) => (
            <div key={label} style={{ display: "flex", alignItems: "center" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 9, minWidth: 78 }}>
                <div style={{ width: 11, height: 11, borderRadius: 99, background: "var(--color-accent)", boxShadow: "0 0 12px rgba(16,185,129,0.5)" }} />
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "#cdd3d7", fontWeight: 500 }}>{label}</span>
              </div>
              {i < FLOW_STEPS.length - 1 && (
                <div style={{ width: 38, height: 1.5, background: "linear-gradient(90deg,#10b981,rgba(16,185,129,0.25))", margin: "0 2px 22px" }} />
              )}
            </div>
          ))}
        </div>
      </section>

      {/* memory layers */}
      <section style={{ maxWidth: "1180px", margin: "0 auto", padding: "34px 32px 80px" }}>
        <div data-testid="landing-memory-layers" style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 18 }}>
          {MEMORY_LAYERS.map((layer) => (
            <div key={layer.tag} style={{ background: "var(--color-inset)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 24 }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#34d399", marginBottom: 12 }}>{layer.tag}</div>
              <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>{layer.title}</div>
              <p style={{ fontSize: 14, lineHeight: 1.6, color: "#8a9298", margin: 0 }}>{layer.desc}</p>
              <div style={{ marginTop: 16, fontFamily: "var(--font-mono)", fontSize: "11.5px", color: "#5b6469", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 12 }}>
                {layer.meta}
              </div>
            </div>
          ))}
        </div>
      </section>
      </div>
    </div>
  );
}
