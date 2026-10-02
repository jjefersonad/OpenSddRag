import { Outlet } from "react-router-dom";
import SearchOverlay from "./features/search/SearchOverlay";
import "./styles/base.css";

/** App layout shell: sidebar + routed content (design D2). */
export default function App() {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "220px 1fr",
        minHeight: "100%",
        background: "var(--color-page)",
      }}
    >
      <aside
        style={{
          background: "var(--color-sidebar)",
          borderRight: "1px solid var(--color-border)",
          padding: "20px",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-mono)",
            color: "var(--color-accent)",
            fontWeight: 600,
          }}
        >
          OpenSddRag
        </span>
      </aside>
      <main style={{ padding: "24px" }}>
        <Outlet />
      </main>
      <SearchOverlay />
    </div>
  );
}
