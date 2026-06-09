// ── Grid Tool Controls ─────────────────────────────────────────────
import { useRef } from "react";
import { useCanvasContext } from "../CanvasContext";

const rowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  padding: "5px 8px",
};

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "rgba(255,255,255,0.6)",
  userSelect: "none",
  minWidth: 60,
};

const sliderStyle: React.CSSProperties = {
  flex: 1,
  minWidth: 0,
};

const spinboxStyle: React.CSSProperties = {
  width: 38,
  background: "rgba(0,0,0,0.4)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 4,
  color: "rgba(255,255,255,0.8)",
  fontSize: 11,
  textAlign: "center",
  padding: "2px 0",
  flexShrink: 0,
};

export default function GridControls() {
  const canvas = useCanvasContext();
  const colorInputRef = useRef<HTMLInputElement>(null);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Show grid checkbox */}
      <div style={rowStyle}>
        <label style={{
          display: "flex", alignItems: "center", gap: 6,
          cursor: "pointer", userSelect: "none",
        }}>
          <input
            type="checkbox"
            checked={canvas.gridShowGrid}
            onChange={(e) => canvas.setGridShowGrid(e.target.checked)}
            style={{ margin: 0, cursor: "pointer", accentColor: "#6fa8ff" }}
          />
          <span style={{ fontSize: 11, color: "rgba(255,255,255,0.7)" }}>
            Show Grid
          </span>
        </label>
      </div>

      {/* Grid size slider + spinbox */}
      <div style={rowStyle}>
        <span style={labelStyle}>Size</span>
        <input
          type="range"
          min={8}
          max={512}
          step={8}
          value={canvas.gridSize}
          onChange={(e) => canvas.setGridSize(Number(e.target.value))}
          style={sliderStyle}
          title={`Grid size: ${canvas.gridSize}px`}
        />
        <input
          type="number"
          min={8}
          max={512}
          step={8}
          value={canvas.gridSize}
          onChange={(e) =>
            canvas.setGridSize(
              Math.max(8, Math.min(512, Number(e.target.value))),
            )
          }
          style={spinboxStyle}
        />
      </div>

      {/* Grid color selector */}
      <div style={rowStyle}>
        <span style={labelStyle}>Color</span>
        <label title="Grid color" style={{ cursor: "pointer", position: "relative" }}>
          <div style={{
            width: 20, height: 20, borderRadius: 4,
            background: canvas.gridColor,
            border: "2px solid rgba(255,255,255,0.2)",
            cursor: "pointer",
          }} />
          <input
            ref={colorInputRef}
            type="color"
            value={canvas.gridColor}
            onChange={(e) => canvas.setGridColor(e.target.value)}
            style={{
              position: "absolute", opacity: 0, width: 1, height: 1,
              pointerEvents: "none",
            }}
            tabIndex={-1}
          />
        </label>
      </div>
    </div>
  );
}
