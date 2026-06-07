import { useRef } from "react";
import Dropdown from "react-bootstrap/Dropdown";
import {
  ZoomIn, ZoomOut, Crosshair, Settings, GripHorizontal,
  Undo2, Redo2, FilePlus, Trash2, Layers,
  MessageSquareHeart,
} from "lucide-react";
import type { ActiveTool, ActiveGridArea } from "./useCanvasState";
import SliderWithSpinbox from "../../components/panels/SliderWithSpinbox";
import { TOOLS, IconBtn, Divider } from "./ToolBarTools";
import ToolBarGrid from "./ToolBarGrid";

export type ToolbarDock = "top" | "bottom";

interface ToolBarProps {
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  showGrid: boolean;
  snapToGrid: boolean;
  zoom: number;
  activeGridArea: ActiveGridArea;
  gridLocked: boolean;
  dock: ToolbarDock;
  onSetActiveTool: (tool: ActiveTool) => void;
  onSetBrushSize: (size: number) => void;
  onSetBrushColor: (color: string) => void;
  onToggleGrid: () => void;
  onToggleSnap: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomReset: () => void;
  onCenterView: () => void;
  onSetGridArea: (area: ActiveGridArea) => void;
  onToggleGridLock: () => void;
  onOpenSettings: () => void;
  onSetDock: (dock: ToolbarDock) => void;
  onUndo: () => void;
  onRedo: () => void;
  onNewDocument: () => void;
  onClearMask?: () => void;
  hasMaskStrokes?: boolean;
  showLayers: boolean;
  onToggleLayers: () => void;
  showArtPanel: boolean;
  onToggleArtPanel: () => void;
}

const DOCK_LABELS: Record<ToolbarDock, string> = {
  top: "Dock Top", bottom: "Dock Bottom",
};

export default function ToolBar({
  activeTool,
  brushSize,
  brushColor,
  showGrid,
  snapToGrid,
  zoom,
  activeGridArea,
  gridLocked,
  dock,
  onSetActiveTool,
  onSetBrushSize,
  onSetBrushColor,
  onToggleGrid,
  onToggleSnap,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onCenterView,
  onSetGridArea,
  onToggleGridLock,
  onOpenSettings,
  onSetDock,
  onUndo,
  onRedo,
  onNewDocument,
  onClearMask,
  hasMaskStrokes = false,
  showLayers,
  onToggleLayers,
  showArtPanel,
  onToggleArtPanel,
}: ToolBarProps) {
  const colorInputRef = useRef<HTMLInputElement>(null);
  const hasBrushOptions =
    activeTool === "brush" ||
    activeTool === "eraser" ||
    activeTool === "mask";
  const zoomPct = `${Math.round(zoom * 100)}%`;

  const containerStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    padding: "4px 8px",
    background: "#161620",
    borderBottom: dock === "top"
      ? "1px solid rgba(255,255,255,0.07)"
      : undefined,
    borderTop: dock === "bottom"
      ? "1px solid rgba(255,255,255,0.07)"
      : undefined,
    flexWrap: "wrap",
    flexShrink: 0,
    userSelect: "none",
    position: "relative",
    zIndex: 100,
  };

  return (
    <div style={containerStyle}>
      {/* ── New document — first icon on the left ────────────────────── */}
      <IconBtn title="New document" onClick={onNewDocument}>
        <FilePlus size={15} strokeWidth={1.75} />
      </IconBtn>

      {/* ── Tools ────────────────────────────────────────────── */}
      {TOOLS.map(({ id, label, key, Icon }) => (
        <IconBtn
          key={id}
          title={`${label} (${key})`}
          active={activeTool === id}
          onClick={() => onSetActiveTool(id)}
        >
          <Icon size={15} strokeWidth={1.75} />
        </IconBtn>
      ))}

      <Divider />

      {/* ── Undo / Redo ───────────────────────────────────────── */}
      <IconBtn title="Undo (Ctrl+Z)" onClick={onUndo}>
        <Undo2 size={15} strokeWidth={1.75} />
      </IconBtn>
      <IconBtn title="Redo (Ctrl+Shift+Z)" onClick={onRedo}>
        <Redo2 size={15} strokeWidth={1.75} />
      </IconBtn>

      <Divider />

      {/* Color swatch — always visible regardless of active tool */}
      <label
        title="Brush color"
        style={{ cursor: "pointer", flexShrink: 0 }}
      >
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: 4,
            background: brushColor,
            border: "2px solid rgba(255,255,255,0.2)",
            cursor: "pointer",
          }}
        />
        <input
          ref={colorInputRef}
          type="color"
          value={brushColor}
          onChange={(e) => onSetBrushColor(e.target.value)}
          style={{
            position: "absolute", opacity: 0,
            width: 1, height: 1, pointerEvents: "none",
          }}
          tabIndex={-1}
        />
      </label>

      {/* Brush size — always visible */}
      <div
        style={{
          display: "flex", alignItems: "center",
          gap: 4, flexShrink: 0,
        }}
      >
        <span style={{
          fontSize: 10, color: "rgba(255,255,255,0.4)",
          whiteSpace: "nowrap",
        }}>
          Size
        </span>
        <input
          type="range"
          min={1}
          max={200}
          step={1}
          value={brushSize}
          onChange={(e) => onSetBrushSize(Number(e.target.value))}
          style={{ width: 80 }}
          title={`Brush size: ${brushSize}px`}
        />
        <input
          type="number"
          min={1}
          max={200}
          value={brushSize}
          onChange={(e) =>
            onSetBrushSize(
              Math.max(1, Math.min(200, Number(e.target.value))),
            )
          }
          style={{
            width: 44,
            background: "rgba(0,0,0,0.4)",
            border: "1px solid rgba(255,255,255,0.15)",
            borderRadius: 4,
            color: "rgba(255,255,255,0.8)",
            fontSize: 11,
            textAlign: "center",
            padding: "2px 0",
          }}
        />
      </div>

      <Divider />

      {/* ── Zoom ──────────────────────────────────────────────── */}
      <IconBtn title="Zoom out" onClick={onZoomOut}>
        <ZoomOut size={15} strokeWidth={1.75} />
      </IconBtn>
      <button
        title="Reset zoom to 100%"
        onClick={onZoomReset}
        style={{
          height: 24,
          padding: "0 6px",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 4,
          background: "transparent",
          color: "rgba(255,255,255,0.6)",
          fontSize: 11,
          fontFamily: "monospace",
          cursor: "pointer",
          flexShrink: 0,
          whiteSpace: "nowrap",
        }}
      >
        {zoomPct}
      </button>
      <IconBtn title="Zoom in" onClick={onZoomIn}>
        <ZoomIn size={15} strokeWidth={1.75} />
      </IconBtn>
      <IconBtn title="Center view" onClick={onCenterView}>
        <Crosshair size={14} strokeWidth={1.75} />
      </IconBtn>

      <Divider />

      {/* ── Active Grid Area ──────────────────────────────────── */}
      <ToolBarGrid
        showGrid={showGrid}
        snapToGrid={snapToGrid}
        activeGridArea={activeGridArea}
        gridLocked={gridLocked}
        onToggleGrid={onToggleGrid}
        onToggleSnap={onToggleSnap}
        onSetGridArea={onSetGridArea}
        onToggleGridLock={onToggleGridLock}
      />

      {/* ── Mask controls ─────────────────────────────────────── */}
      {(activeTool === "mask" || hasMaskStrokes) && (
        <>
          <Divider />
          <IconBtn title="Clear mask" danger onClick={onClearMask}>
            <Trash2 size={14} strokeWidth={1.75} />
          </IconBtn>
        </>
      )}

      {/* ── Spacer — push right-side items to the end ──────── */}
      <div style={{ flex: 1, minWidth: 0 }} />

      {/* ── Settings & Dock ───────────────────────────────────── */}
      <IconBtn
        title={showLayers ? "Hide layers" : "Show layers"}
        active={showLayers}
        onClick={onToggleLayers}
      >
        <Layers size={15} strokeWidth={1.75} />
      </IconBtn>
      <IconBtn
        title={showArtPanel ? "Hide art panel" : "Show art panel"}
        active={showArtPanel}
        onClick={onToggleArtPanel}
      >
        <MessageSquareHeart size={15} strokeWidth={1.75} />
      </IconBtn>
      <IconBtn title="Canvas settings" onClick={onOpenSettings}>
        <Settings size={15} strokeWidth={1.75} />
      </IconBtn>

      <Dropdown>
        <Dropdown.Toggle
          as="button"
          title="Toolbar position"
          style={{
            width: 30,
            height: 30,
            padding: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "none",
            borderRadius: 5,
            background: "transparent",
            color: "rgba(var(--theme-text-rgb), 0.4)",
            cursor: "pointer",
          }}
        >
          <GripHorizontal size={15} strokeWidth={1.75} />
        </Dropdown.Toggle>
        <Dropdown.Menu
          style={{
            background: "#1e1e2e",
            border: "1px solid rgba(255,255,255,0.1)",
            minWidth: 130, zIndex: 9999,
          }}
        >
          {(["top", "bottom"] as ToolbarDock[]).map((d) => (
            <Dropdown.Item
              key={d}
              onClick={() => onSetDock(d)}
              active={dock === d}
              style={{
                fontSize: 12, color: "rgba(255,255,255,0.7)",
              }}
            >
              {DOCK_LABELS[d]}
            </Dropdown.Item>
          ))}
        </Dropdown.Menu>
      </Dropdown>
    </div>
  );
}
