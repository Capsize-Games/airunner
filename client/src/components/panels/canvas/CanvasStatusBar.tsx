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
  transition: "background 0.1s, color 0.1s",
};

const btnActiveStyle: React.CSSProperties = {
  ...btnStyle,
  color: "var(--bs-primary)",
};

function onFooterBtnEnter(e: React.MouseEvent<HTMLButtonElement>) {
  const bg = e.currentTarget.style.background;
  if (!bg.includes("bs-primary") && !bg.includes("rgba(99,153,255")) {
    e.currentTarget.style.background = "rgba(255,255,255,0.08)";
    e.currentTarget.style.color = "rgba(255,255,255,0.85)";
  }
}

function onFooterBtnLeave(e: React.MouseEvent<HTMLButtonElement>) {
  const bg = e.currentTarget.style.background;
  if (!bg.includes("bs-primary") && !bg.includes("rgba(99,153,255")) {
    e.currentTarget.style.background = "none";
    e.currentTarget.style.color = "rgba(255,255,255,0.4)";
  }
}

export interface CanvasStatusBarProps {
  documentWidth: number;
  documentHeight: number;
  zoom: number;
  gridWidth: number;
  gridHeight: number;
  activeLayer: CanvasLayer | null;
  isFitToView: boolean;
  isCenterView: boolean;
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
  isFitToView,
  isCenterView,
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
      {activeLayer && <span>Layer: {activeLayer.name}</span>}

      <div className="flex-grow-1" />

      {/* Zoom controls */}
      <div className="d-flex align-items-center" style={{ gap: 1 }}>
        <button style={btnStyle} title="Zoom out" onClick={onZoomOut}
          onMouseEnter={onFooterBtnEnter} onMouseLeave={onFooterBtnLeave}>
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
            transition: "background 0.1s, border-color 0.1s, color 0.1s",
          }}
          title="Reset zoom to 100%"
          onClick={onZoomReset}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.08)";
            e.currentTarget.style.borderColor = "rgba(255,255,255,0.3)";
            e.currentTarget.style.color = "rgba(255,255,255,0.9)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
            e.currentTarget.style.color = "rgba(255,255,255,0.5)";
          }}
        >
          {zoomPct}
        </button>
        <button style={btnStyle} title="Zoom in" onClick={onZoomIn}
          onMouseEnter={onFooterBtnEnter} onMouseLeave={onFooterBtnLeave}>
          <ZoomIn size={13} strokeWidth={1.75} />
        </button>
        <button
          style={isCenterView ? btnActiveStyle : btnStyle}
          title={isCenterView ? "Center view (active)" : "Center view"}
          onClick={onCenterView}
          onMouseEnter={onFooterBtnEnter}
          onMouseLeave={onFooterBtnLeave}
        >
          <Crosshair size={13} strokeWidth={1.75} />
        </button>
        <button
          style={isFitToView ? btnActiveStyle : btnStyle}
          title={isFitToView ? "Fit to view (active)" : "Fit to view"}
          onClick={onFitView}
          onMouseEnter={onFooterBtnEnter}
          onMouseLeave={onFooterBtnLeave}
        >
          <Expand size={13} strokeWidth={1.75} />
        </button>
      </div>
    </div>
  );
}
