export interface TabBarTab {
  key: string;
  label: string;
  count?: number;
}

/**
 * TabBar (REQ-020, design D7): the prototype's underline tab row — tabs on a
 * single row over a 1px bottom border, 14px-scale labels in secondary colour,
 * and the active tab in primary colour with a 2px accent underline. Counts
 * render as small neutral mono pills next to the label.
 */
export default function TabBar({
  tabs,
  active,
  onSelect,
}: {
  tabs: TabBarTab[];
  active: string;
  onSelect: (key: string) => void;
}) {
  return (
    <div
      role="tablist"
      style={{
        display: "flex",
        gap: "2px",
        borderBottom: "1px solid var(--color-border)",
        marginBottom: "24px",
        overflowX: "auto",
      }}
    >
      {tabs.map((tab) => {
        const isActive = tab.key === active;
        return (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onSelect(tab.key)}
            style={{
              padding: "11px 16px",
              fontSize: "13.5px",
              cursor: "pointer",
              background: "transparent",
              border: "none",
              borderBottom: `2px solid ${isActive ? "var(--color-accent)" : "transparent"}`,
              color: isActive ? "var(--color-text-primary)" : "var(--color-text-secondary)",
              fontWeight: isActive ? 600 : 400,
              display: "flex",
              alignItems: "center",
              gap: "7px",
              whiteSpace: "nowrap",
            }}
          >
            {tab.label}
            {typeof tab.count === "number" ? (
              <span
                className="tab-count"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10.5px",
                  color: "var(--color-text-tertiary)",
                  background: "rgba(255,255,255,0.06)",
                  borderRadius: "5px",
                  padding: "1px 6px",
                }}
              >
                {tab.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}