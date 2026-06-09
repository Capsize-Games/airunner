import { MessageSquareHeart, FilePlus, Settings } from "lucide-react";
import {
  Move, SquareDashed, Lasso, Wand, Crop,
  PaintBucket, Pointer, Type, Pipette, Search,
  Brush, Eraser, Layers, Images, Grid3x3, Ruler,
} from "lucide-react";
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
  onNewDocument: () => void;
  onOpenSettings: () => void;
  activeAssetTab: "layers" | "images" | null;
  onToggleLayers: () => void;
  onToggleImages: () => void;
  showImagePrompt: boolean;
  onToggleImagePrompt: () => void;
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
  onNewDocument,
  onOpenSettings,
  activeAssetTab,
  onToggleLayers,
  onToggleImages,
  showImagePrompt,
  onToggleImagePrompt,
}: Props) {
  const toolBtn = (id: string, Icon: React.ComponentType<{ size?: number; strokeWidth?: number }>) => {
    const isActive = !showImagePrompt && activeTool === id;
    return (
      <button
        key={id}
        title={TOOLS.find((t) => t.id === id)?.label ?? id}
        onClick={() => onToolChange(id as ActiveTool)}
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
    <button key={title} title={title} onClick={onClick} style={btn}>
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
      {/* Row 1: header — new doc left, settings right */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 6px 4px 6px",
        margin: "0 -6px 2px -6px",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
      }}>
        {iconBtn("New Document", FilePlus, onNewDocument)}
        {iconBtn("Canvas Settings", Settings, onOpenSettings)}
      </div>

      {/* Row 2: image-prompt toggle + all canvas tools */}
      <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
        {toggleBtn(showImagePrompt, MessageSquareHeart, "Toggle Image Prompt", onToggleImagePrompt)}
        {TOOLS.map((t) => toolBtn(t.id, t.Icon))}
      </div>

      {/* Row 3: layer / image browser toggles */}
      <div style={{
        display: "flex", alignItems: "center", gap: 2,
        padding: "4px 6px",
        margin: "2px -6px",
        borderTop: "1px solid rgba(255,255,255,0.07)",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
      }}>
        {toggleBtn(activeAssetTab === "layers", Layers, "Layers Panel", onToggleLayers)}
        {toggleBtn(activeAssetTab === "images", Images, "Images Panel", onToggleImages)}
      </div>
    </div>
  );
}
