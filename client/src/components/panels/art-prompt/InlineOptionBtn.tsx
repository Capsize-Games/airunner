import type { ReactNode } from "react";

export default function InlineOptionBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: "2px 8px",
        fontSize: 10,
        borderRadius: 4,
        border: "1px solid rgba(255,255,255,0.12)",
        background: active
          ? "rgba(var(--theme-primary-rgb), 0.15)"
          : "transparent",
        color: active
          ? "var(--bs-primary)"
          : "var(--theme-text-secondary)",
        cursor: "pointer",
      }}
      onMouseEnter={(e) => {
        if (!active)
          (e.currentTarget as HTMLButtonElement).style.background =
            "rgba(255,255,255,0.06)";
      }}
      onMouseLeave={(e) => {
        if (!active)
          (e.currentTarget as HTMLButtonElement).style.background =
            "transparent";
      }}
    >
      {children}
    </button>
  );
}
