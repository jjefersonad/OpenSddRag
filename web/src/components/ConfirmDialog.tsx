interface Props {
  title: string;
  message: string;
  confirmLabel: string;
  busy?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onClose: () => void;
}

/** Blocking confirm for deletes. The page stays put until Cancel or Confirm. */
export default function ConfirmDialog({ title, message, confirmLabel, busy, error, onConfirm, onClose }: Props) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "grid",
        placeItems: "center",
        zIndex: 30,
      }}
    >
      <div
        style={{
          background: "var(--color-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "12px",
          padding: "24px",
          width: "380px",
          display: "grid",
          gap: "12px",
        }}
      >
        <h2 style={{ margin: 0, fontSize: "16px" }}>{title}</h2>
        <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: "14px", lineHeight: 1.5 }}>{message}</p>
        {error ? (
          <p role="alert" style={{ color: "var(--color-danger)", margin: 0 }}>
            {error}
          </p>
        ) : null}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
          <button type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            style={{
              background: "var(--color-danger)",
              color: "#fff",
              border: "none",
              borderRadius: "8px",
              padding: "8px 14px",
              fontWeight: 600,
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
