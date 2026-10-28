import { type CSSProperties, type ReactNode } from "react";

const CODE_BLOCK_STYLE: CSSProperties = {
  margin: 0,
  padding: "10px 12px",
  fontFamily: "var(--font-mono)",
  fontSize: "12px",
  color: "var(--color-text-primary)",
  background: "var(--color-inset)",
  border: "1px solid var(--color-border)",
  borderRadius: "8px",
  overflowX: "auto",
  whiteSpace: "pre",
};

const P: CSSProperties = {
  color: "var(--color-text-secondary)",
  lineHeight: 1.65,
  fontSize: "14px",
  margin: "0 0 12px",
  textWrap: "pretty",
};

const STEP_TITLE: CSSProperties = {
  margin: 0,
  fontSize: "14px",
  fontWeight: 600,
  color: "var(--color-text-primary)",
};

export function CodeBlock({ children }: { children: string }) {
  return (
    <pre style={CODE_BLOCK_STYLE}>
      <code style={{ fontFamily: "var(--font-mono)" }}>{children}</code>
    </pre>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <div style={{ display: "flex", gap: "12px", margin: "0 0 18px" }}>
      <span
        aria-hidden="true"
        style={{
          flexShrink: 0,
          width: "22px",
          height: "22px",
          borderRadius: "999px",
          background: "rgba(16, 185, 129, 0.12)",
          border: "1px solid rgba(16, 185, 129, 0.35)",
          color: "var(--color-accent-hover)",
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          display: "grid",
          placeItems: "center",
          marginTop: "1px",
        }}
      >
        {n}
      </span>
      <div style={{ display: "flex", flexDirection: "column", gap: "8px", minWidth: 0, flex: 1 }}>
        <h3 style={STEP_TITLE}>{title}</h3>
        {children}
      </div>
    </div>
  );
}

function Note({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        margin: "0 0 14px",
        padding: "10px 12px",
        background: "rgba(96, 165, 250, 0.08)",
        border: "1px solid rgba(96, 165, 250, 0.22)",
        borderRadius: "10px",
        color: "var(--color-text-secondary)",
        fontSize: "13.5px",
        lineHeight: 1.55,
      }}
    >
      {children}
    </div>
  );
}

export const QUICKSTART_COMMANDS = [
  {
    command: "docker compose up -d",
    description: "Start PostgreSQL/pgvector (port 54326), the MCP server (port 8000) and the dashboard (port 3001).",
  },
  {
    command: "opensddrag-server init",
    description: "Run migrations and seed global SDD skills. Docker already migrates on startup — this is for a local Python install.",
  },
  {
    command: "npx opensddrag init --server http://localhost:8000 --api-key <key> --tools claude,opencode --yes",
    description: "From your project root: register the project, write MCP config, and install slash commands for Claude Code, Cursor (.mcp.json) and OpenCode.",
  },
];

export function QuickstartBody() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      {QUICKSTART_COMMANDS.map((entry) => (
        <div key={entry.command} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <CodeBlock>{entry.command}</CodeBlock>
          <p style={{ ...P, margin: 0, fontSize: "13.5px" }}>{entry.description}</p>
        </div>
      ))}
    </div>
  );
}

export function ServerSetupBody() {
  return (
    <>
      <p style={P}>
        The recommended path is Docker. You get the database, the MCP HTTP endpoint and the dashboard
        together. A local Python install is only needed if you are developing the server itself.
      </p>

      <h3 style={{ ...STEP_TITLE, marginBottom: "10px" }}>Docker (recommended)</h3>
      <Step n={1} title="Start the stack">
        <p style={{ ...P, margin: 0 }}>From the OpenSddRag repository root:</p>
        <CodeBlock>{"docker compose up -d"}</CodeBlock>
      </Step>
      <Step n={2} title="What comes up">
        <p style={{ ...P, margin: 0 }}>
          PostgreSQL/pgvector on <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>localhost:54326</code>
          , MCP + management API on <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>localhost:8000</code>
          , dashboard on <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>http://localhost:3001</code>.
          The container runs migrations and seeds the SDD pipeline on boot.
        </p>
      </Step>
      <Step n={3} title="Check the MCP endpoint">
        <p style={{ ...P, margin: 0 }}>
          Auth is on by default. A 401 means the server is up and waiting for a Bearer API key:
        </p>
        <CodeBlock>{"curl -i http://localhost:8000/mcp/"}</CodeBlock>
      </Step>
      <Step n={4} title="Two different secrets">
        <Note>
          The dashboard login is the management token (<code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>MANAGEMENT_API_TOKEN</code>
          , Docker default <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>123456</code>
          ). Claude Code, Cursor and OpenCode use a separate MCP API key created on{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/keys</code>. Do not mix them.
        </Note>
      </Step>

      <h3 style={{ ...STEP_TITLE, margin: "8px 0 10px" }}>Local Python (development)</h3>
      <Step n={1} title="Install and migrate">
        <CodeBlock>{`cd mcp-server
cp .env.example .env
uv pip install -e .
opensddrag-server init
opensddrag-server server start --transport sse --port 8000`}</CodeBlock>
      </Step>
      <Step n={2} title="Environment">
        <p style={{ ...P, margin: 0 }}>
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>DATABASE_URL</code> must reach pgvector
          (Compose maps it to port 54326 on the host).{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>AUTH_ENABLED=true</code> (default) requires
          an MCP API key.{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>WEB_ORIGIN</code> should match the dashboard
          origin (Compose default <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>http://localhost:3001</code>
          ) so the browser can call <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/api/v1</code>.
        </p>
      </Step>
    </>
  );
}

export function DashboardBody() {
  return (
    <>
      <Step n={1} title="Open the dashboard">
        <p style={{ ...P, margin: 0 }}>
          Go to <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>http://localhost:3001</code>. Docs
          and the landing page are public; projects and API keys require a login.
        </p>
      </Step>
      <Step n={2} title="Sign in with the management token">
        <p style={{ ...P, margin: 0 }}>
          Paste <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>MANAGEMENT_API_TOKEN</code>. With
          unmodified Docker Compose that value is{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>123456</code>. Change it in production.
        </p>
      </Step>
      <Step n={3} title="What you can do there">
        <p style={{ ...P, margin: 0 }}>
          Create and inspect projects, browse live changes and artifacts, search with ⌘K, manage harness rules, and
          create MCP API keys on <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/keys</code>. The
          dashboard talks to <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/api/v1</code> — it is
          not an MCP client.
        </p>
      </Step>
    </>
  );
}

export function CliClientBody() {
  return (
    <>
      <p style={P}>
        The npm package <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>opensddrag</code> is a CLI.
        Run it from the project you want the agent to work in — not from this repository, unless this is the project.
      </p>
      <Step n={1} title="Create an MCP API key first">
        <p style={{ ...P, margin: 0 }}>
          Dashboard → API keys → New key, or{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>opensddrag-server key create --description &quot;local dev&quot;</code>
          . Copy the plaintext; it is shown once.
        </p>
      </Step>
      <Step n={2} title="Connect the project">
        <CodeBlock>{`cd my-project
npx opensddrag init --server http://localhost:8000 --api-key <key>`}</CodeBlock>
        <p style={{ ...P, margin: 0 }}>
          Interactive init asks which AI tools and which pipelines to install. For scripts:
        </p>
        <CodeBlock>
          {"npx opensddrag init --server http://localhost:8000 --api-key <key> --tools claude,opencode --flow sdd --yes"}
        </CodeBlock>
      </Step>
      <Step n={3} title="Useful flags">
        <p style={{ ...P, margin: 0 }}>
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>--project</code> slug (default: directory
          name) · <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>--tools claude,opencode</code> ·{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>--flow sdd,docs</code> extra pipelines ·{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>--yes</code> skip prompts (SDD only unless{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>--flow</code> is set).
        </p>
      </Step>
      <Step n={4} title="Check the wiring">
        <CodeBlock>{"npx opensddrag status"}</CodeBlock>
        <p style={{ ...P, margin: 0 }}>
          Confirms local files, slash commands, and that the server can see the project. Env vars{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>OPENSDDRAG_SERVER_URL</code> and{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>OPENSDDRAG_API_KEY</code> work in place of
          flags.
        </p>
      </Step>
    </>
  );
}

const MCP_JSON = `{
  "mcpServers": {
    "opensddrag": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer <mcp-api-key>"
      }
    }
  }
}`;

const OPENCODE_JSON = `{
  "mcp": {
    "opensddrag": {
      "type": "remote",
      "url": "http://localhost:8000/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer <mcp-api-key>"
      }
    }
  }
}`;

export function ClaudeCodeBody() {
  return (
    <>
      <p style={P}>
        Claude Code and Cursor both read <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>.mcp.json</code>{" "}
        in the project root. Slash commands for Claude Code live under{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>.claude/commands/opsr/</code>.
      </p>
      <Step n={1} title="Let init write the files">
        <CodeBlock>{"npx opensddrag init --tools claude --api-key <mcp-api-key> --yes"}</CodeBlock>
        <p style={{ ...P, margin: 0 }}>
          Writes <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>.mcp.json</code>, skills in{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>.claude/skills/opensddrag-*/</code>,
          commands in <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>.claude/commands/opsr/</code>,
          and an OpenSddRag section in <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>CLAUDE.md</code>
          .
        </p>
      </Step>
      <Step n={2} title="Or paste this into .mcp.json">
        <CodeBlock>{MCP_JSON}</CodeBlock>
      </Step>
      <Step n={3} title="Reload Claude Code">
        <p style={{ ...P, margin: 0 }}>
          Restart the session or reconnect MCP so the{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>opensddrag</code> tools appear (Cursor:
          reload the window if tools are missing). A 401 means the Bearer key is missing or wrong — create a new key
          on <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/keys</code> and update the header. Do
          not put the dashboard management token here.
        </p>
      </Step>
      <Step n={4} title="Run the pipeline">
        <p style={{ ...P, margin: 0 }}>
          Slash commands are <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:propose</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:spec</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:design</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:tasks</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:apply</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:verify</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:archive</code>. Start with{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:status</code> if you are unsure
          where a change left off.
        </p>
      </Step>
    </>
  );
}

export function OpenCodeBody() {
  return (
    <>
      <p style={P}>
        OpenCode uses <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>opencode.json</code> for MCP
        and installs native skills/commands under{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>.opencode/</code>.
      </p>
      <Step n={1} title="Let init write the files">
        <CodeBlock>{"npx opensddrag init --tools opencode --api-key <mcp-api-key> --yes"}</CodeBlock>
        <p style={{ ...P, margin: 0 }}>
          You can combine tools in one run:{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>--tools claude,opencode</code>.
        </p>
      </Step>
      <Step n={2} title="Or paste this into opencode.json">
        <CodeBlock>{OPENCODE_JSON}</CodeBlock>
      </Step>
      <Step n={3} title="Enable the MCP server in OpenCode">
        <p style={{ ...P, margin: 0 }}>
          Confirm <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>opensddrag</code> is listed as a
          remote MCP server and enabled. Restart OpenCode after changing the JSON. Tools should include{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>create_artifact</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>search_semantic</code>, and the rest of
          the OpenSddRag set.
        </p>
      </Step>
      <Step n={4} title="Use the same slash commands">
        <p style={{ ...P, margin: 0 }}>
          Commands land in <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>.opencode/commands/opsr/</code>
          . Invoke <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:propose</code> (and the rest
          of the SDD sequence) the same way as in Claude Code.
        </p>
      </Step>
    </>
  );
}

export function ApiKeysBody() {
  return (
    <>
      <p style={P}>
        MCP clients send <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>Authorization: Bearer &lt;api-key&gt;</code>{" "}
        to <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/mcp</code>. Keys can be global or scoped
        to one project. The dashboard never stores the plaintext after create.
      </p>
      <Step n={1} title="Create from the dashboard">
        <p style={{ ...P, margin: 0 }}>
          Sign in → API keys → create. Copy the key immediately, then pass it to{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>opensddrag init --api-key</code> or paste
          it into <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>.mcp.json</code> /{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>opencode.json</code>.
        </p>
      </Step>
      <Step n={2} title="Or create from the server CLI">
        <CodeBlock>{`cd mcp-server && source .venv/bin/activate
opensddrag-server key create --description "local dev"`}</CodeBlock>
      </Step>
      <Step n={3} title="Revoke">
        <p style={{ ...P, margin: 0 }}>
          Revoke on <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/keys</code> or with{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>opensddrag-server key revoke &lt;id&gt;</code>
          . Connected MCP clients then get 401 until you install a new key.
        </p>
      </Step>
    </>
  );
}

const PIPELINE_MANIFEST = `{
  "flow": "docs",
  "kinds": [
    { "kind": "brief" },
    { "kind": "draft" },
    { "kind": "publish" }
  ],
  "lifecycle": [
    { "name": "Brief", "kinds": ["brief"] },
    { "name": "Draft", "kinds": ["draft"] },
    { "name": "Publish", "kinds": ["publish"] }
  ],
  "harness_triggers": ["on_draft", "on_publish"],
  "skills": ["opensddrag-docs-draft"],
  "commands": [{ "name": "draft" }, { "name": "publish" }],
  "claude_md_section": "## OpenSddRag — docs pipeline\\n"
}`;

const KIND_CARD: CSSProperties = {
  background: "var(--color-inset)",
  border: "1px solid var(--color-border)",
  borderRadius: "10px",
  padding: "12px 14px",
  display: "flex",
  flexDirection: "column",
  gap: "6px",
};

const TH: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "10px",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "var(--color-text-tertiary)",
  textAlign: "left",
  fontWeight: 500,
  padding: "8px 10px",
  borderBottom: "1px solid var(--color-border)",
};

const TD: CSSProperties = {
  padding: "8px 10px",
  borderBottom: "1px solid rgba(255,255,255,0.06)",
  fontSize: "13px",
  color: "var(--color-text-secondary)",
  verticalAlign: "top",
};

function KindCard({
  kind,
  command,
  headings,
  children,
}: {
  kind: string;
  command?: string;
  headings: string;
  children: ReactNode;
}) {
  return (
    <div data-testid={`docs-kind-${kind}`} style={KIND_CARD}>
      <div style={{ display: "flex", gap: "10px", alignItems: "baseline", flexWrap: "wrap" }}>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            color: "var(--color-accent-hover)",
            background: "rgba(16, 185, 129, 0.1)",
            border: "1px solid rgba(16, 185, 129, 0.25)",
            borderRadius: "999px",
            padding: "2px 10px",
          }}
        >
          {kind}
        </span>
        {command ? (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--color-text-tertiary)" }}>
            {command}
          </span>
        ) : null}
      </div>
      <p style={{ ...P, margin: 0, fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-text-primary)" }}>
        {headings}
      </p>
      <p style={{ ...P, margin: 0, fontSize: "13.5px" }}>{children}</p>
    </div>
  );
}

const SDD_PHASES = [
  { phase: "Propose", command: "/opsr:propose", kinds: "proposal" },
  { phase: "Spec", command: "/opsr:spec", kinds: "spec, test (scenario)" },
  { phase: "Design", command: "/opsr:design", kinds: "design" },
  { phase: "Tasks", command: "/opsr:tasks", kinds: "task, test (unit)" },
  { phase: "Apply", command: "/opsr:apply", kinds: "task (status) + unit tests" },
  { phase: "Verify", command: "/opsr:verify", kinds: "test (scenario status)" },
  { phase: "Sync", command: "/opsr:sync", kinds: "delta specs → main specs" },
  { phase: "Archive", command: "/opsr:archive", kinds: "change artifacts archived" },
];

export function HarnessBody() {
  return (
    <>
      <p style={P}>
        The harness is per-project, not SDD-only. <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>always</code>{" "}
        rules are injected by <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>get_working_context</code>{" "}
        at every session start. Phase-gate rules are returned by{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>get_harness_checklist</code>. Manage them from
        the dashboard Harness tab, <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:harness</code>
        , or the MCP tools <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>add_rule</code> /{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>list_rules</code>.
      </p>
      <Step n={1} title="Triggers add_rule accepts today">
        <p style={{ ...P, margin: 0 }}>
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>always</code> ·{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>on_spec</code> ·{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>on_apply</code> ·{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>on_verify</code> ·{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>on_archive</code>. Custom pipeline manifests
          may name other triggers as data; creating a rule still has to use this enum.
        </p>
      </Step>
      <Step n={2} title="Severity">
        <p style={{ ...P, margin: 0 }}>
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>error</code> must be satisfied before the
          gate completes. <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>warning</code> should be
          addressed. <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>info</code> is guidance.
        </p>
      </Step>
      <Step n={3} title="Seeded rule">
        <p style={{ ...P, margin: 0 }}>
          Every project gets <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>tdd-first</code> (
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>on_apply</code>, error) from{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>opensddrag init</code>. Disable it only when
          the project has a stated different testing stance.
        </p>
      </Step>
    </>
  );
}

export function PipelinesBody() {
  return (
    <>
      <p style={P}>
        A <strong style={{ color: "var(--color-text-primary)", fontWeight: 600 }}>pipeline</strong> (flow) is the unit
        of workflow — not a hardcoded SDD sequence. Each pipeline is a named pack of artifact kinds, optional
        lifecycle phases, harness triggers, skills and slash commands, stored as data. The dashboard derives progress
        from that lifecycle, so a new pipeline renders without UI changes.
      </p>
      <p style={P}>
        SDD is the built-in pipeline (<code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>flow: sdd</code>
        ). Any other pipeline declares its own phases and its own artifact formats. Validation is always{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>(flow, kind)</code>: built-in SDD rules for{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>spec</code> /{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>task</code>, otherwise the kind&apos;s{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>required_headings</code> /{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>required_metadata_keys</code>, otherwise a
        structural fallback.
      </p>

      <h3 style={{ ...STEP_TITLE, margin: "8px 0 10px" }}>What every pipeline declares</h3>
      <p style={P}>
        The manifest is the contract. Lifecycle phases are ordered display names mapped to kinds (closing phases may
        use an empty kinds list). Artifact &quot;formats&quot; live on the kind — headings and metadata keys — not as
        a global SDD schema.
      </p>
      <ul style={{ ...P, paddingLeft: "18px", margin: "0 0 16px" }}>
        <li>
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>flow</code> — kebab-case slug
        </li>
        <li>
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>kinds</code> — artifact types, each with
          optional <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>required_headings</code> and{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>required_metadata_keys</code>
        </li>
        <li>
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>lifecycle</code> — ordered phases the
          dashboard uses for progress
        </li>
        <li>
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>commands</code> /{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>skills</code> /{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>harness_triggers</code> — what agents run
        </li>
      </ul>

      <Step n={1} title="Install pipelines with the CLI">
        <CodeBlock>{"npx opensddrag init --flow sdd,docs --yes"}</CodeBlock>
        <p style={{ ...P, margin: 0 }}>
          SDD commands stay bare (<code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:propose</code>
          ). Every other pipeline is namespaced{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:&lt;flow&gt;:&lt;command&gt;</code>.
          Omitting <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>--flow</code> with{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>--yes</code> stays SDD-only.
        </p>
      </Step>
      <Step n={2} title="Register a custom pipeline">
        <p style={{ ...P, margin: 0 }}>
          JSON, snake_case. The slug must be kebab-case. After registration,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>create_artifact</code> /{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>validate_artifact</code> accept the new
          kinds and the dashboard shows the declared phases — no server code.
        </p>
        <CodeBlock>{PIPELINE_MANIFEST}</CodeBlock>
        <CodeBlock>{"opensddrag-server register-flow ./docs-manifest.json"}</CodeBlock>
        <p style={{ ...P, margin: 0 }}>
          Or call the MCP tool <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>register_flow</code>.
          To also ship skills/commands, add a pack under{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>client/src/templates/flows/&lt;slug&gt;/</code>
          .
        </p>
        <Note>
          A manifest may list any <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>harness_triggers</code>{" "}
          strings. <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>add_rule</code> currently accepts
          only <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>always</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>on_spec</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>on_apply</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>on_verify</code>,{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>on_archive</code>. Map custom pipeline
          gates onto those values until the enum is opened.
        </Note>
      </Step>

      <h3 style={{ ...STEP_TITLE, margin: "12px 0 10px" }}>Built-in pipeline: SDD</h3>
      <p style={P}>
        Spec-Driven Development is one registered flow. Its lifecycle and artifact formats below apply only when{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>flow=sdd</code> (the project default unless
        you change it). A docs or ops pipeline you register does not use proposal/spec/design — it uses the kinds you
        declared.
      </p>
      <p style={P}>
        Run phases in order. Each command reads the previous artifact from memory and writes the next. Utility
        commands that are not lifecycle phases:{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:explore</code>,{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:continue</code>,{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:status</code>,{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:flow</code>,{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:search</code>,{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>/opsr:harness</code>.
      </p>
      <div
        data-testid="docs-sdd-phases"
        style={{ overflowX: "auto", margin: "0 0 16px", border: "1px solid var(--color-border)", borderRadius: "10px" }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={TH}>Phase</th>
              <th style={TH}>Command</th>
              <th style={TH}>Writes</th>
            </tr>
          </thead>
          <tbody>
            {SDD_PHASES.map((row) => (
              <tr key={row.phase}>
                <td style={{ ...TD, color: "var(--color-text-primary)", fontWeight: 600 }}>{row.phase}</td>
                <td style={{ ...TD, fontFamily: "var(--font-mono)", fontSize: "12px" }}>{row.command}</td>
                <td style={TD}>{row.kinds}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 style={{ ...STEP_TITLE, margin: "4px 0 10px" }}>SDD artifact formats</h3>
      <p style={P}>
        Each SDD kind has a heading contract. Names follow{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>&lt;change&gt;-proposal</code>,{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>&lt;change&gt;-&lt;capability&gt;-spec</code>
        , <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>&lt;change&gt;-design</code>,{" "}
        <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>&lt;change&gt;-task-&lt;group&gt;-&lt;N&gt;</code>
        . For a custom pipeline, put the equivalent headings on the kind in the manifest instead of copying this
        list.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "8px" }}>
        <KindCard kind="proposal" command="/opsr:propose" headings="## Why · ## What Changes · ## Capabilities · ## Impact">
          Named change entry. Capabilities listed here become specs. Keep impact and out-of-scope explicit so later
          phases do not grow the change.
        </KindCard>
        <KindCard
          kind="spec"
          command="/opsr:spec"
          headings="## Purpose · ## Requirements · ### Requirement: REQ-NNN · #### Scenario: WHEN / THEN"
        >
          One spec per capability. SHALL/MUST language. Delta specs set{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>metadata.is_delta=true</code> and use
          ADDED / MODIFIED / REMOVED / RENAMED. After the spec, confirm scenarios — each confirmed WHEN/THEN becomes a{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>test</code> artifact (
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>level=scenario</code>
          ).
        </KindCard>
        <KindCard kind="design" command="/opsr:design" headings="## Decisions · ## Risks / Trade-offs">
          Chosen approach plus rejected alternatives. Do not skip the rejected list — that is how later sessions avoid
          reopening settled calls.
        </KindCard>
        <KindCard kind="task" command="/opsr:tasks" headings="## Goal · ## Acceptance Criteria · ## Dependencies">
          Atomic, verifiable units. A testable task must link a unit{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>test</code> artifact. Tasks with no runtime
          behaviour set <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>metadata.test_exempt=true</code>{" "}
          and a <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>## Reason</code> heading.
        </KindCard>
        <KindCard
          kind="test"
          headings="metadata.level = scenario | unit · metadata.test_status = pending → failing → passing"
        >
          First-class artifacts, not a side table. Apply is RED → GREEN → REFACTOR per unit test. Verify derives
          scenario status from linked unit tests.
        </KindCard>
      </div>
    </>
  );
}
