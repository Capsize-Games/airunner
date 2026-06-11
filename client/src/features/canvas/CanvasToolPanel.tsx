import { MessageSquareHeart, Wrench } from "lucide-react";
import {
  Move, SquareDashed, Lasso, Wand, Crop,
  PaintBucket, Pointer, Type, Pipette, Search,
  Brush, Eraser, Grid3x3, Ruler,
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

  const iconBtn = (
    title: string,
    Icon: React.ComponentType<{ size?: number; strokeWidth?: number }>,
    onClick: () => void,
  ) => (
    <button key={title} title={title} onClick={onClick} style={btn}
      onMouseEnter={onBtnEnter} onMouseLeave={onBtnLeave}>
      <Icon size={14} strokeWidth={1.75} />
    </button>
  );

  const toggleBtn = (
    active: boolean,
    Icon: React.ComponentType<{ size?: number; strokeWidth?: number }>,
    title: string,
    onClick: () => void,
  ) => (
    <button
      key={title}
      title={title}
      onClick={onClick}
      onMouseEnter={onBtnEnter}
      onMouseLeave={onBtnLeave}
      style={{
        ...btn,
        background: active ? "rgba(99,153,255,0.22)" : "transparent",
        color: active ? "var(--bs-primary)" : "rgba(255,255,255,0.35)",
        boxShadow: active ? "inset 0 0 0 1.5px rgba(99,153,255,0.55)" : "none",
      }}
    >
      <Icon size={14} strokeWidth={1.75} />
    </button>
  );

  return (
    <div
      style={{
        display: "flex", flexDirection: "column", gap: 2, padding: "4px 6px",
        background: "#161620",
        userSelect: "none", flexShrink: 0,
      }}
    >
      {/* ── Palette toggle buttons ────────────────────────────────────
       * These two buttons switch between showing the image prompt or the
       * canvas tool palette. Only one can be active at a time. */}
      <div style={{ display: "flex", alignItems: "center", gap: 2, padding: "4px 6px", margin: "0 -6px 2px", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
        {toggleBtn(showImagePrompt, MessageSquareHeart, "Toggle Image Prompt", onToggleImagePrompt)}
        {toggleBtn(showCanvasTools, Wrench, "Canvas Tools", onToggleCanvasTools)}
      </div>

      {/* ── Art prompt palette ────────────────────────────────────────
       * Shown only when the image-prompt palette is active. These
       * buttons mirror the toolbar at the bottom of the chat prompt.
       * Each dispatches a custom event that ArtPromptPanel listens for
       * to open the corresponding settings panel/popup. */}
      {showImagePrompt && (
        <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap", padding: "4px 6px", margin: "0 -6px", borderBottom: "1px solid rgba(255,255,255,0.07)", background: "#12121c" }}>
          <button key="art-model-options" title="Art model options" style={btn}
            onMouseEnter={onBtnEnter} onMouseLeave={onBtnLeave}
            onClick={() => window.dispatchEvent(new CustomEvent("art:action", { detail: "modelOptions" }))}>
            <LucideIcon name="sparkles" size={14} />
          </button>
          <button key="embeddings" title="Embeddings" style={btn}
            onMouseEnter={onBtnEnter} onMouseLeave={onBtnLeave}
            onClick={() => window.dispatchEvent(new CustomEvent("art:action", { detail: "embeddings" }))}>
            <LucideIcon name="scan-text" size={14} />
          </button>
          <button key="lora" title="LoRA" style={btn}
            onMouseEnter={onBtnEnter} onMouseLeave={onBtnLeave}
            onClick={() => window.dispatchEvent(new CustomEvent("art:action", { detail: "lora" }))}>
            <LucideIcon name="puzzle" size={14} />
          </button>
          <button key="gen-settings" title="Generation settings" style={btn}
            onMouseEnter={onBtnEnter} onMouseLeave={onBtnLeave}
            onClick={() => window.dispatchEvent(new CustomEvent("art:action", { detail: "settings" }))}>
            <LucideIcon name="settings-2" size={14} />
          </button>
          <button key="seed" title="Seed randomization" style={btn}
            onMouseEnter={onBtnEnter} onMouseLeave={onBtnLeave}
            onClick={() => window.dispatchEvent(new CustomEvent("art:action", { detail: "seed" }))}>
            <LucideIcon name="shuffle" size={14} />
          </button>
          <button key="gen-type" title="Generation type" style={btn}
            onMouseEnter={onBtnEnter} onMouseLeave={onBtnLeave}
            onClick={() => window.dispatchEvent(new CustomEvent("art:action", { detail: "genType" }))}>
            <LucideIcon name="image-plus" size={14} />
          </button>
          <button key="image-size" title="Image size" style={btn}
            onMouseEnter={onBtnEnter} onMouseLeave={onBtnLeave}
            onClick={() => window.dispatchEvent(new CustomEvent("art:action", { detail: "imageSize" }))}>
            <LucideIcon name="ruler-dimension-line" size={14} />
          </button>
        </div>
      )}

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
