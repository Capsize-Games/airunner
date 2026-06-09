import { useState } from "react";
import LucideIcon from "../../shared/LucideIcon";

export default function ToolbarToggle({
  active,
  title,
  onClick,
  icon,
}: {
  active: boolean;
  title: string;
  onClick?: () => void;
  icon: string;
}) {
  const [hovered, setHovered] = useState(false);

  let bg = "transparent";
  if (active && hovered) bg = "rgba(13,110,253,0.3)";
  else if (active) bg = "rgba(13,110,253,0.18)";
  else if (hovered) bg = "rgba(255,255,255,0.08)";

  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 26,
        height: 26,
        padding: 0,
        background: bg,
        border: active
          ? "1px solid rgba(13,110,253,0.4)"
          : "1px solid transparent",
        cursor: "pointer",
        borderRadius: 4,
        color: active ? "var(--bs-primary)" : "rgba(255,255,255,0.4)",
        flexShrink: 0,
        transition: "background 0.1s, border-color 0.1s",
      }}
    >
      <LucideIcon name={icon} size={15} />
    </button>
  );
}
