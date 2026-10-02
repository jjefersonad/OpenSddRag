/** Design-system reference page (route /docs, design D2). */
export default function DocsPage() {
  return (
    <section>
      <h1 style={{ margin: "0 0 12px", fontSize: "20px" }}>Design system</h1>
      <p className="label">Tokens</p>
      <ul style={{ color: "var(--color-text-secondary)" }}>
        <li>Backgrounds: page / sidebar / card / inset</li>
        <li>Accent: #10b981 (hover #34d399, on-accent #04140d)</li>
        <li>Semantic: amber #fbbf24 · blue #60a5fa · violet #a78bfa · red #f87171</li>
        <li>Fonts: IBM Plex Sans / IBM Plex Mono</li>
      </ul>
    </section>
  );
}
