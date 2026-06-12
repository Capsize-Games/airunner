import {
  Move, SquareDashed, Lasso, Wand, Crop,
  PaintBucket, Pointer, Type, Pipette, Search,
  Brush, Eraser, Grid3x3, Ruler, MessageSquareHeart, Palette,
} from "lucide-react";
import LucideIcon from "../../components/shared/LucideIcon";
import type { ActiveTool } from "./useCanvasState";

const TOOLS: { id: string; label: string; Icon: React.ComponentType<{ size?: number; strokeWidth?: number }> }[] = [
  { id: "move",    label: "Move (V)",      Icon: Move },
  { id: "select",  label: "Select (S)",    Icon: SquareDashed },
  { id: "lasso",   label: "Free Select",   Icon: Lasso },
  { id: "wand",    label: "Fuzzy Select",  Icon: Wand },
  { id: "crop",    label: "Crop",          Icon: Crop },
  { id: "bucket",  label: "Bucket Fill",   Icon: PaintBucket },
  { id: "smudge",  label: "Smudge",        Icon: Pointer },
  { id: "text",    label: "Text",          Icon: Type },
  { id: "pipette", label: "Color Picker",  Icon: Pipette },
  { id: "zoom",    label: "Zoom",          Icon: Search },
  { id: "brush",   label: "Brush (B)",     Icon: Brush },
  { id: "eraser",  label: "Eraser (E)",    Icon: Eraser },
  { id: "grid",    label: "Grid",          Icon: Grid3x3 },
  { id: "ruler",   label: "Ruler",         Icon: Ruler },
];

interface Props {
  activeTool: ActiveTool;
  onToolChange: (tool: ActiveTool) => void;
  showImagePrompt: boolean;
  onToggleImagePrompt: () => void;
  showCanvasTools: boolean;
  onToggleCanvasTools: () => void;
  onCollapse?: () => void;
}

const btn: React.CSSProperties = {
  display: "flex", alignItems: "center", justifyContent: "center",
  width: 32, height: 28, padding: 0,
  background: "transparent", border: "none",
  borderRadius: 4, cursor: "pointer", flexShrink: 0,
  color: "rgba(255,255,255,0.5)",
  transition: "background 0.1s, color 0.1s",
};

export default function CanvasToolPanel({
  activeTool,
  onToolChange,
  showImagePrompt,
  onToggleImagePrompt,
  showCanvasTools,
  onToggleCanvasTools,
  onCollapse,
}: Props) {
  const onBtnEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
    const bg = e.currentTarget.style.background;
    // Only apply hover if not already in an active/blue state
    if (!bg.includes("rgba(99,153,255")) {
      e.currentTarget.style.background = "rgba(255,255,255,0.08)";
      e.currentTarget.style.color = "rgba(255,255,255,0.85)";
    }
  };

  const onBtnLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
    const bg = e.currentTarget.style.background;
    if (!bg.includes("rgba(99,153,255")) {
      e.currentTarget.style.background = "transparent";
      e.currentTarget.style.color = "rgba(255,255,255,0.5)";
    }
  };

  const toolBtn = (id: string, Icon: React.ComponentType<{ size?: number; strokeWidth?: number }>) => {
    const isActive = !showImagePrompt && activeTool === id;
    return (
      <button
        key={id}
        title={TOOLS.find((t) => t.id === id)?.label ?? id}
        onClick={() => onToolChange(id as ActiveTool)}
        onMouseEnter={onBtnEnter}
        onMouseLeave={onBtnLeave}
        style={{
          ...btn,
          background: isActive ? "rgba(99,153,255,0.22)" : "transparent",
          color: isActive ? "#6fa8ff" : "rgba(255,255,255,0.5)",
          boxShadow: isActive ? "inset 0 0 0 1.5px rgba(99,153,255,0.55)" : "none",
        }}
      >
        <Icon size={14} strokeWidth={1.75} />
      </button>
    );
  };

  const tabBtnBase: React.CSSProperties = {
    flex: 1, padding: "5px 4px", background: "transparent", border: "none",
    fontSize: 11, cursor: "pointer", display: "flex", alignItems: "center",
    justifyContent: "center", gap: 4, transition: "color 0.15s, border-color 0.15s",
  };

  const collapseBtnStyle: React.CSSProperties = {
    background: "none", border: "none", cursor: "pointer",
    padding: "5px 6px", color: "rgba(255,255,255,0.35)",
    display: "flex", alignItems: "center", justifyContent: "center",
    transition: "color 0.15s",
  };

  const TABS: { id: string; active: boolean; icon: React.ComponentType<{ size?: number; strokeWidth?: number }>; title: string; onClick: () => void }[] = [
    { id: "image-prompt", active: showImagePrompt, icon: MessageSquareHeart, title: "Image Prompt", onClick: onToggleImagePrompt },
    { id: "canvas-tools", active: showCanvasTools, icon: Palette, title: "Canvas Tools", onClick: onToggleCanvasTools },
  ];

  return (
    <div
      style={{
        display: "flex", flexDirection: "column", gap: 2, padding: "4px 6px",
        background: "#161620",
        userSelect: "none", flexShrink: 0,
      }}
    >
      {/* ── Tab bar with collapse chevron ─────────────────────────────
       * Collapse chevron on the left, then palette toggle tabs styled
       * to match the right panel tab appearance. */}
      <div className="d-flex flex-shrink-0" style={{ background: "#161620", margin: "0 -6px", borderBottom: "1px solid rgba(255,255,255,0.07)", gap: 0 }}>
        <button
          type="button"
          title="Collapse panel"
          onClick={onCollapse}
          style={collapseBtnStyle}
          onMouseEnter={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.85)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.35)"; }}
        >
          <LucideIcon name="chevron-left" size={12} />
        </button>
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            title={t.title}
            onClick={t.onClick}
            style={{
              ...tabBtnBase,
              background: t.active ? "var(--theme-panel-bg)" : "transparent",
              borderBottom: t.active ? "2px solid var(--bs-primary)" : "2px solid transparent",
              color: t.active ? "var(--bs-primary)" : "rgba(255,255,255,0.45)",
            }}
            onMouseEnter={(e) => {
              if (!t.active)
                e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            }}
            onMouseLeave={(e) => {
              if (!t.active)
                e.currentTarget.style.background = "transparent";
            }}
          >
            <t.icon size={12} strokeWidth={1.75} />
          </button>
        ))}
      </div>


      {/* ── Palette of tools ──────────────────────────────────────────
       * Shown only when the canvas-tools palette is active. Each button
       * selects a drawing/editing mode (move, brush, eraser, etc.). */}
      {showCanvasTools && (
        <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap", padding: "4px 6px", margin: "0 -6px", borderBottom: "1px solid rgba(255,255,255,0.07)", background: "#12121c" }}>
          {TOOLS.map((t) => toolBtn(t.id, t.Icon))}
        </div>
      )}
    </div>
  );
}
