import type { CanvasLayer } from "../../../features/canvas/useCanvasState";

export interface CanvasStatusBarProps {
  documentWidth: number;
  documentHeight: number;
  zoom: number;
  gridWidth: number;
  gridHeight: number;
  activeLayer: CanvasLayer | null;
  connected: boolean;
}

export default function CanvasStatusBar({
  documentWidth,
  documentHeight,
  zoom,
  gridWidth,
  gridHeight,
  activeLayer,
  connected,
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
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          color: connected
            ? "rgba(0,200,100,0.7)"
            : "rgba(255,150,50,0.6)",
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: connected
              ? "rgb(0,200,100)"
              : "rgb(255,150,50)",
            display: "inline-block",
          }}
        />
        {connected ? "Live" : "Reconnecting\u2026"}
      </span>
    </div>
  );
}
