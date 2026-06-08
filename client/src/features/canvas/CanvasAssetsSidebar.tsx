import { useState, useCallback, useRef, useEffect } from "react";
import { SquareDashed, Brush, Eraser, Move, Undo2, Redo2 } from "lucide-react";
import CanvasLayersSidebar from "./CanvasLayersSidebar";
import ImageBrowserPanel from "../../components/panels/ImageBrowserPanel";
import LucideIcon from "../../components/shared/LucideIcon";
import { useCanvasContext } from "./CanvasContext";
import type { ActiveTool } from "./useCanvasState";

const TOOLS: { id: ActiveTool; label: string; Icon: React.ComponentType<{ size?: number; strokeWidth?: number }> }[] = [
  { id: "move",   label: "Move (V)",   Icon: Move },
  { id: "select", label: "Select (S)", Icon: SquareDashed },
  { id: "brush",  label: "Brush (B)",  Icon: Brush },
  { id: "eraser", label: "Eraser (E)", Icon: Eraser },
];

type AssetTab = "layers" | "images";

const LS_W         = "airunner_assets_sidebar_w";
const LS_TAB       = "airunner_assets_sidebar_tab";
const LS_COLLAPSED = "airunner_assets_sidebar_collapsed";

function loadWidth(): number {
  try {
    const v = localStorage.getItem(LS_W);
    if (v === null) {
      const old = localStorage.getItem("airunner_layers_sidebar_w");
      return old !== null ? Number(old) : 220;
    }
    return Number(v);
  } catch { return 220; }
}

const TABS: { id: AssetTab; icon: string; label: string }[] = [
  { id: "layers", icon: "layers", label: "Layers" },
  { id: "images", icon: "images", label: "Images" },
];

const railBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  cursor: "pointer",
  color: "rgba(255,255,255,0.4)",
  padding: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  borderRadius: 4,
  width: 28,
  height: 28,
  flexShrink: 0,
};

const tabBtnBase: React.CSSProperties = {
  flex: 1,
  padding: "5px 4px",
  background: "transparent",
  border: "none",
  fontSize: 11,
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 4,
  transition: "color 0.15s, border-color 0.15s",
};

function toolBtnStyle(active: boolean): React.CSSProperties {
  return {
    flex: 1,
    height: 28,
    padding: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    background: active ? "rgba(99,153,255,0.22)" : "transparent",
    color: active ? "#6fa8ff" : "rgba(255,255,255,0.45)",
    boxShadow: active ? "inset 0 0 0 1.5px rgba(99,153,255,0.55)" : "none",
  };
}

function iconBtnStyle(disabled?: boolean): React.CSSProperties {
  return {
    width: 26,
    height: 26,
    padding: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    border: "none",
    borderRadius: 4,
    cursor: disabled ? "default" : "pointer",
    background: "transparent",
    color: disabled ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.45)",
    flexShrink: 0,
  };
}

export default function CanvasAssetsSidebar() {
  const canvas = useCanvasContext();
  const colorInputRef = useRef<HTMLInputElement>(null);
  const [tab, setTab] = useState<AssetTab>(() => {
    try { return (localStorage.getItem(LS_TAB) as AssetTab) ?? "layers"; }
    catch { return "layers"; }
  });
  const [width, setWidth] = useState(loadWidth);
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(LS_COLLAPSED) === "true"; }
    catch { return false; }
  });
  const dragging = useRef(false);
  const startX = useRef(0);
  const startW = useRef(0);

  useEffect(() => {
    try { localStorage.setItem(LS_W, String(width)); } catch { /* */ }
  }, [width]);

  useEffect(() => {
    try { localStorage.setItem(LS_TAB, tab); } catch { /* */ }
  }, [tab]);

  useEffect(() => {
    try { localStorage.setItem(LS_COLLAPSED, String(collapsed)); } catch { /* */ }
  }, [collapsed]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    startX.current = e.clientX;
    startW.current = width;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const delta = ev.clientX - startX.current;
      setWidth(Math.max(180, Math.min(500, startW.current - delta)));
    };

    const onUp = () => {
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [width]);

  const expand = (toTab?: AssetTab) => {
    if (toTab) setTab(toTab);
    setCollapsed(false);
  };

  const brushActive = canvas.activeTool === "brush" || canvas.activeTool === "eraser";

  if (collapsed) {
    return (
      <div
        style={{
          width: 32,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          background: "#181824",
          borderLeft: "1px solid rgba(255,255,255,0.07)",
          padding: "4px 0",
          gap: 2,
          overflow: "hidden",
        }}
      >
        <button style={railBtnStyle} title="Expand panel" onClick={() => expand()}>
          <LucideIcon name="chevron-left" size={14} />
        </button>
        <div style={{ width: "60%", height: 1, background: "rgba(255,255,255,0.07)", margin: "2px 0" }} />
        {TABS.map((t) => (
          <button
            key={t.id}
            style={{ ...railBtnStyle, color: tab === t.id ? "var(--bs-primary)" : "rgba(255,255,255,0.4)" }}
            title={t.label}
            onClick={() => expand(t.id)}
          >
            <LucideIcon name={t.icon} size={14} />
          </button>
        ))}
      </div>
    );
  }

  return (
    <div style={{ width, flexShrink: 0, display: "flex", flexDirection: "row", overflow: "hidden" }}>
      {/* Resize handle — left edge */}
      <div
        onMouseDown={handleMouseDown}
        style={{ width: 4, cursor: "col-resize", flexShrink: 0, background: "transparent", transition: "background 0.15s" }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "rgba(99,153,255,0.3)"; }}
        onMouseLeave={(e) => { if (!dragging.current) (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
      />

      {/* Panel content */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "#181824", overflow: "hidden", minWidth: 0 }}>

        {/* Collapse header row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            flexShrink: 0,
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            padding: "2px 4px",
          }}
        >
          <span style={{ flex: 1, fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.25)", letterSpacing: "0.06em", paddingLeft: 4 }}>ASSETS</span>
          <button
            type="button"
            onClick={() => setCollapsed(true)}
            title="Collapse panel"
            style={{ ...railBtnStyle, width: 24, height: 24, color: "rgba(255,255,255,0.25)" }}
          >
            <LucideIcon name="chevron-right" size={13} />
          </button>
        </div>

        {/* Tool buttons + undo/redo row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            flexShrink: 0,
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            padding: "4px 6px",
            gap: 2,
          }}
        >
          {TOOLS.map(({ id, label, Icon }) => (
            <button
              key={id}
              title={label}
              onClick={() => canvas.setActiveTool(id)}
              style={toolBtnStyle(canvas.activeTool === id)}
            >
              <Icon size={14} strokeWidth={1.75} />
            </button>
          ))}

          <div style={{ width: 1, height: 18, background: "rgba(255,255,255,0.1)", margin: "0 3px", flexShrink: 0 }} />

          <button title="Undo (Ctrl+Z)" style={iconBtnStyle()} onClick={canvas.undo}>
            <Undo2 size={13} strokeWidth={1.75} />
          </button>
          <button title="Redo (Ctrl+Shift+Z)" style={iconBtnStyle()} onClick={canvas.redo}>
            <Redo2 size={13} strokeWidth={1.75} />
          </button>
        </div>

        {/* Brush controls row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "5px 8px",
            flexShrink: 0,
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            opacity: brushActive ? 1 : 0.35,
            pointerEvents: brushActive ? "auto" : "none",
          }}
        >
          {/* Color swatch */}
          <label title="Brush color" style={{ cursor: "pointer", flexShrink: 0, position: "relative" }}>
            <div
              style={{
                width: 20,
                height: 20,
                borderRadius: 4,
                background: canvas.brushColor,
                border: "2px solid rgba(255,255,255,0.2)",
                cursor: "pointer",
              }}
            />
            <input
              ref={colorInputRef}
              type="color"
              value={canvas.brushColor}
              onChange={(e) => canvas.setBrushColor(e.target.value)}
              style={{ position: "absolute", opacity: 0, width: 1, height: 1, pointerEvents: "none" }}
              tabIndex={-1}
            />
          </label>

          {/* Size slider */}
          <input
            type="range"
            min={1}
            max={200}
            step={1}
            value={canvas.brushSize}
            onChange={(e) => canvas.setBrushSize(Number(e.target.value))}
            style={{ flex: 1, minWidth: 0 }}
            title={`Brush size: ${canvas.brushSize}px`}
          />

          {/* Size spinbox */}
          <input
            type="number"
            min={1}
            max={200}
            value={canvas.brushSize}
            onChange={(e) => canvas.setBrushSize(Math.max(1, Math.min(200, Number(e.target.value))))}
            style={{
              width: 38,
              background: "rgba(0,0,0,0.4)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 4,
              color: "rgba(255,255,255,0.8)",
              fontSize: 11,
              textAlign: "center",
              padding: "2px 0",
              flexShrink: 0,
            }}
          />
        </div>

        {/* Tab bar */}
        <div style={{ display: "flex", flexShrink: 0, borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              style={{
                ...tabBtnBase,
                background: tab === t.id ? "var(--theme-panel-bg)" : "transparent",
                borderBottom: tab === t.id ? "2px solid var(--bs-primary)" : "2px solid transparent",
                color: tab === t.id ? "var(--bs-primary)" : "rgba(255,255,255,0.45)",
              }}
            >
              <LucideIcon name={t.icon} size={12} />
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{ flex: 1, overflow: "hidden", minHeight: 0, display: "flex", flexDirection: "column" }}>
          {tab === "layers" ? <CanvasLayersSidebar /> : <ImageBrowserPanel />}
        </div>
      </div>
    </div>
  );
}
