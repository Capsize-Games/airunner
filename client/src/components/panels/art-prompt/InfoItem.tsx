import type { ReactNode, MouseEvent } from "react";
import LucideIcon from "../../shared/LucideIcon";

export default function InfoItem({
  label,
  value,
  icon,
  editing,
  dimmed,
  onClick,
  onMouseDown,
  children,
  editor,
}: {
  label: string;
  value?: string;
  icon?: string;
  editing?: boolean;
  dimmed?: boolean;
  onClick?: (e: MouseEvent) => void;
  onMouseDown?: (e: MouseEvent) => void;
  children?: ReactNode;
  editor?: ReactNode;
}) {
  return (
    <div
      onClick={onClick}
      onMouseDown={onMouseDown}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "3px 10px",
        borderBottom: "1px solid rgba(255,255,255,0.04)",
        cursor: onClick ? "pointer" : "default",
      }}
      onMouseEnter={(e) => {
        if (onClick)
          (e.currentTarget as HTMLDivElement).style.background =
            "rgba(255,255,255,0.03)";
      }}
      onMouseLeave={(e) => {
        if (onClick)
          (e.currentTarget as HTMLDivElement).style.background = "transparent";
      }}
    >
      {icon && <LucideIcon name={icon} size={10} />}
      <span
        style={{
          color: "var(--theme-text-secondary)",
          opacity: 0.55,
          fontSize: 10,
          width: 80,
          flexShrink: 0,
        }}
      >
        {label}
      </span>
      {editing && editor ? (
        <div
          style={{ flex: 1, minWidth: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          {editor}
        </div>
      ) : value !== undefined ? (
        <span
          style={{
            color: "var(--theme-text)",
            opacity: dimmed ? 0.35 : 1,
            fontSize: 10,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            flex: 1,
          }}
        >
          {value}
        </span>
      ) : null}
      {children}
    </div>
  );
}
