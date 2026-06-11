import { SquareDashed, Brush, Eraser, Move, Undo2, Redo2 } from "lucide-react";
import { useCanvasContext } from "../CanvasContext";
import type { ActiveTool } from "../useCanvasState";

const TOOLS: { id: ActiveTool; label: string; Icon: React.ComponentType<{ size?: number; strokeWidth?: number }> }[] = [
  { id: "move",   label: "Move (V)",   Icon: Move },
  { id: "select", label: "Select (S)", Icon: SquareDashed },
  { id: "brush",  label: "Brush (B)",  Icon: Brush },
  { id: "eraser", label: "Eraser (E)", Icon: Eraser },
];

function toolBtnStyle(active: boolean): React.CSSProperties {
  return {
    flex: 1, height: 28, padding: 0,
    display: "flex", alignItems: "center", justifyContent: "center",
    border: "none", borderRadius: 4, cursor: "pointer",
    background: active ? "rgba(99,153,255,0.22)" : "transparent",
    color: active ? "#6fa8ff" : "rgba(255,255,255,0.45)",
    boxShadow: active ? "inset 0 0 0 1.5px rgba(99,153,255,0.55)" : "none",
    transition: "background 0.1s, color 0.1s",
  };
}

const iconBtnStyle: React.CSSProperties = {
  width: 26, height: 26, padding: 0,
  display: "flex", alignItems: "center", justifyContent: "center",
  border: "none", borderRadius: 4, cursor: "pointer",
  background: "transparent", color: "rgba(255,255,255,0.45)",
  flexShrink: 0, transition: "background 0.1s, color 0.1s",
};

function onToolBtnEnter(e: React.MouseEvent<HTMLButtonElement>) {
  const btn = e.currentTarget;
  // Only apply hover if not in active state
  const isActive = btn.style.background.includes("rgba(99,153,255");
  if (!isActive) {
    btn.style.background = "rgba(255,255,255,0.08)";
    btn.style.color = "rgba(255,255,255,0.85)";
  }
}

function onToolBtnLeave(e: React.MouseEvent<HTMLButtonElement>) {
  const btn = e.currentTarget;
  const isActive = btn.style.background.includes("rgba(99,153,255");
  if (!isActive) {
    btn.style.background = "transparent";
    btn.style.color = "rgba(255,255,255,0.45)";
  }
}

export default function ToolRow() {
  const canvas = useCanvasContext();
  return (
    <div
      className="d-flex align-items-center flex-shrink-0 border-b-subtle"
      style={{ padding: "4px 6px", gap: 2 }}
    >
      {TOOLS.map(({ id, label, Icon }) => (
        <button
          key={id}
          title={label}
          onClick={() => canvas.setActiveTool(id)}
          style={toolBtnStyle(canvas.activeTool === id)}
          onMouseEnter={onToolBtnEnter}
          onMouseLeave={onToolBtnLeave}
        >
          <Icon size={14} strokeWidth={1.75} />
        </button>
      ))}
      <div className="sep-v" />
      <button title="Undo (Ctrl+Z)" style={iconBtnStyle} onClick={canvas.undo}
        onMouseEnter={onToolBtnEnter} onMouseLeave={onToolBtnLeave}>
        <Undo2 size={13} strokeWidth={1.75} />
      </button>
      <button title="Redo (Ctrl+Shift+Z)" style={iconBtnStyle} onClick={canvas.redo}
        onMouseEnter={onToolBtnEnter} onMouseLeave={onToolBtnLeave}>
        <Redo2 size={13} strokeWidth={1.75} />
      </button>
    </div>
  );
}
