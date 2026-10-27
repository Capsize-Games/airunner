import { ZoomIn, ZoomOut, Crosshair, Expand } from "lucide-react";
import type { CanvasLayer } from "../../../features/canvas/useCanvasState";

const btnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  cursor: "pointer",
  color: "rgba(255,255,255,0.4)",
  padding: "0 3px",
  display: "flex",
  alignItems: "center",
  height: 20,
  borderRadius: 3,
  flexShrink: 0,
};

const btnActiveStyle: React.CSSProperties = {
  ...btnStyle,
  color: "var(--bs-primary)",
};

export interface CanvasStatusBarProps {
  documentWidth: number;
  documentHeight: number;
  zoom: number;
  gridWidth: number;
  gridHeight: number;
  activeLayer: CanvasLayer | null;
  zoomMode: "fit" | "locked";
  onZoomOut: () => void;
  onZoomReset: () => void;
  onZoomIn: () => void;
  onCenterView: () => void;
  onFitView: () => void;
}

export default function CanvasStatusBar({
  documentWidth,
  documentHeight,
  zoom,
  gridWidth,
  gridHeight,
  activeLayer,
  zoomMode,
  onZoomOut,
  onZoomReset,
  onZoomIn,
  onCenterView,
  onFitView,
}: CanvasStatusBarProps) {
  const zoomPct = `${Math.round(zoom * 100)}%`;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        padding: "3px 10px",
        background: "#111118",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        fontSize: 11,
        fontFamily: "monospace",
        color: "rgba(255,255,255,0.4)",
        flexShrink: 0,
        gap: 12,
      }}
    >
      <span>{documentWidth} &times; {documentHeight}</span>
      <span>Grid: {gridWidth} &times; {gridHeight}</span>
      {activeLayer && <span>Layer: {activeLayer.name}</span>}

      <div style={{ flex: 1 }} />

      {/* Zoom controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 1 }}>
        <button style={btnStyle} title="Zoom out" onClick={onZoomOut}>
          <ZoomOut size={13} strokeWidth={1.75} />
        </button>
        <button
          style={{
            height: 20,
            padding: "0 5px",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 3,
            background: "transparent",
            color: "rgba(255,255,255,0.5)",
            fontSize: 11,
            fontFamily: "monospace",
            cursor: "pointer",
            flexShrink: 0,
            whiteSpace: "nowrap",
          }}
          title="Reset zoom to 100%"
          onClick={onZoomReset}
        >
          {zoomPct}
        </button>
        <button style={btnStyle} title="Zoom in" onClick={onZoomIn}>
          <ZoomIn size={13} strokeWidth={1.75} />
        </button>
        <button style={btnStyle} title="Center view" onClick={onCenterView}>
          <Crosshair size={13} strokeWidth={1.75} />
        </button>
        <button
          style={zoomMode === "fit" ? btnActiveStyle : btnStyle}
          title={zoomMode === "fit" ? "Fit to view (active)" : "Fit to view"}
          onClick={onFitView}
        >
          <Expand size={13} strokeWidth={1.75} />
        </button>
      </div>
    </div>
  );
}
