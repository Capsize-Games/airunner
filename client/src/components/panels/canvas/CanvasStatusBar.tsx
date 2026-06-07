import type { CanvasLayer } from "../../../features/canvas/useCanvasState";

export interface CanvasStatusBarProps {
  documentWidth: number;
  documentHeight: number;
  zoom: number;
  gridWidth: number;
  gridHeight: number;
  activeLayer: CanvasLayer | null;
}

export default function CanvasStatusBar({
  documentWidth,
  documentHeight,
  zoom,
  gridWidth,
  gridHeight,
  activeLayer,
}: CanvasStatusBarProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "3px 10px",
        background: "#111118",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        fontSize: 11,
        fontFamily: "monospace",
        color: "rgba(255,255,255,0.4)",
        flexShrink: 0,
      }}
    >
      <span>{documentWidth} &times; {documentHeight}</span>
      <span>Zoom: {Math.round(zoom * 100)}%</span>
      <span>Grid: {gridWidth} &times; {gridHeight}</span>
      {activeLayer && <span>Layer: {activeLayer.name}</span>}
    </div>
  );
}
