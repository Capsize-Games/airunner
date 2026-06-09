import LucideIcon from "../../shared/LucideIcon";

export default function PanelIconBtn({
  icon,
  title,
  active,
  onClick,
}: {
  icon: string;
  title: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 24,
        height: 24,
        padding: 0,
        background: active ? "rgba(255,255,255,0.08)" : "transparent",
        border: "none",
        cursor: "pointer",
        borderRadius: 4,
        color: active ? "var(--bs-primary)" : "rgba(255,255,255,0.4)",
        flexShrink: 0,
        transition: "color 0.1s, background 0.1s",
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
      <LucideIcon name={icon} size={13} />
    </button>
  );
}
