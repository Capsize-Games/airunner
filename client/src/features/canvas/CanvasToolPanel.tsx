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

type GenType = "txt2img" | "img2img" | "inpaint";

interface Props {
  activeTool: ActiveTool;
  onToolChange: (tool: ActiveTool) => void;
  showImagePrompt: boolean;
  onToggleImagePrompt: () => void;
  showCanvasTools: boolean;
  onToggleCanvasTools: () => void;
  activeArtAction: string | null;
  onArtAction: (action: string | null) => void;
  generationType: GenType;
  onGenerationTypeChange: (v: GenType) => void;
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
  activeArtAction,
  onArtAction,
  generationType,
  onGenerationTypeChange,
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

      {/* ── Generation type toggle row ─────────────────────────────────
       * Shown above the art prompt palette. Three mutually exclusive
       * toggle buttons: txt-to-img, img-to-img, inpaint. */}
      {showImagePrompt && (
        <div style={{ display: "flex", alignItems: "center", gap: 2, padding: "4px 6px", margin: "0 -6px", borderBottom: "1px solid rgba(255,255,255,0.07)", background: "#12121c" }}>
          {([
            { id: "txt2img" as GenType, title: "TXT-TO-IMG" },
            { id: "img2img" as GenType, title: "IMG-TO-IMG" },
            { id: "inpaint" as GenType, title: "INPAINT" },
          ] as { id: GenType; title: string }[]).map(({ id, title }) => {
            const active = generationType === id;
            return (
              <button
                key={id}
                title={title}
                onClick={() => onGenerationTypeChange(id)}
                onMouseEnter={onBtnEnter}
                onMouseLeave={onBtnLeave}
                style={{
                  ...btn,
                  background: active ? "rgba(99,153,255,0.22)" : "transparent",
                  color: active ? "var(--bs-primary)" : "rgba(255,255,255,0.35)",
                  boxShadow: active ? "inset 0 0 0 1.5px rgba(99,153,255,0.55)" : "none",
                  width: "auto", height: 26,
                  padding: "0 8px",
                }}
              >
                <span style={{ whiteSpace: "nowrap", fontSize: 9, fontWeight: 600, letterSpacing: "0.03em", fontVariant: "small-caps" }}>
                  {title}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* ── Art prompt palette ────────────────────────────────────────
       * Shown below the gen-type row. Each toggles inline settings in
       * the tool panel. */}
      {showImagePrompt && (
        <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap", padding: "4px 6px", margin: "0 -6px", borderBottom: "1px solid rgba(255,255,255,0.07)", background: "#12121c" }}>
          {[
            { id: "modelOptions", name: "sparkles",    title: "Art model options" },
            { id: "embeddings",   name: "scan-text",   title: "Embeddings" },
            { id: "lora",         name: "puzzle",      title: "LoRA" },
            { id: "settings",     name: "settings-2",  title: "Generation settings" },
            { id: "seed",         name: "shuffle",     title: "Seed randomization" },
            { id: "imageSize",    name: "ruler-dimension-line", title: "Image size" },
          ].map((item) => {
            const isActive = activeArtAction === item.id;
            return (
              <button
                key={item.id}
                title={item.title}
                onClick={() => onArtAction(isActive ? null : item.id)}
                onMouseEnter={onBtnEnter}
                onMouseLeave={onBtnLeave}
                style={{
                  ...btn,
                  background: isActive ? "rgba(99,153,255,0.22)" : "transparent",
                  color: isActive ? "var(--bs-primary)" : "rgba(255,255,255,0.35)",
                  boxShadow: isActive ? "inset 0 0 0 1.5px rgba(99,153,255,0.55)" : "none",
                }}
              >
                <LucideIcon name={item.name} size={14} />
              </button>
            );
          })}
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
