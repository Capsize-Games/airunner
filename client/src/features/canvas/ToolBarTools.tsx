import {
  SquareDashed, Brush, Eraser, Move,
} from "lucide-react";
import type { ActiveTool } from "./useCanvasState";

/** Inline SVG for the lasso (free-select) tool icon. */
function LassoIcon({
  size = 14,
  strokeWidth = 1.75,
}: {
  size?: number; strokeWidth?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M7 22C4.5 20.5 3 18 3 15c0-3.5 2.5-8 6-11C13 2 20 5 20 10c0 4-4 8-10 7-2 0-4-1-5-2.5" />
      <circle cx="10" cy="17" r="1.5" />
    </svg>
  );
}

/**
 * Tool definitions consumed by the main ToolBar component.
 */
export const TOOLS: {
  id: ActiveTool;
  label: string;
  key: string;
  Icon: React.ComponentType<{
    size?: number; strokeWidth?: number;
  }>;
}[] = [
  { id: "select", label: "Select", key: "S", Icon: SquareDashed },
  { id: "lasso",  label: "Lasso",  key: "L", Icon: LassoIcon },
  { id: "brush",  label: "Brush",  key: "B", Icon: Brush },
  { id: "eraser", label: "Eraser", key: "E", Icon: Eraser },
  { id: "move",   label: "Move",   key: "V", Icon: Move },
];

interface IconBtnProps {
  title: string;
  active?: boolean;
  danger?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}

/**
 * Icon button used in the toolbar (supports an active/highlighted state).
 *
 * Note: there is a separate, simpler IconBtn in IconBtn.tsx used by the
 * layers sidebar. Do not conflate the two.
 */
export function IconBtn({
  title,
  active,
  danger,
  disabled,
  onClick,
  children,
}: IconBtnProps) {
  return (
    <button
      title={title}
      disabled={disabled}
      onClick={onClick}
      style={{
        width: 30,
        height: 30,
        padding: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        border: "none",
        borderRadius: 5,
        flexShrink: 0,
        cursor: disabled ? "default" : "pointer",
        background: active ? "rgba(99,153,255,0.22)" : "transparent",
        color: disabled ? "rgba(var(--theme-text-rgb), 0.2)" :
               danger ? "rgba(255,100,100,0.8)" :
               active ? "#6fa8ff" : "rgba(var(--theme-text-rgb), 0.55)",
        boxShadow: active
          ? "inset 0 0 0 1.5px rgba(99,153,255,0.55)"
          : "none",
        transition: "background 0.1s, color 0.1s",
      }}
      onMouseEnter={(e) => {
        if (!active && !disabled) {
          (e.currentTarget as HTMLButtonElement).style.background =
            "rgba(var(--theme-text-rgb), 0.07)";
          (e.currentTarget as HTMLButtonElement).style.color =
            "rgba(var(--theme-text-rgb), 0.9)";
        }
      }}
      onMouseLeave={(e) => {
        if (!active && !disabled) {
          (e.currentTarget as HTMLButtonElement).style.background =
            "transparent";
          (e.currentTarget as HTMLButtonElement).style.color =
            disabled
              ? "rgba(var(--theme-text-rgb), 0.2)"
              : "rgba(var(--theme-text-rgb), 0.55)";
        }
      }}
    >
      {children}
    </button>
  );
}

/**
 * Thin vertical divider rendered between toolbar sections.
 */
export function Divider() {
  return (
    <div style={{
      width: 1, height: 20,
      background: "rgba(255,255,255,0.1)",
      flexShrink: 0,
      margin: "0 2px",
    }} />
  );
}
