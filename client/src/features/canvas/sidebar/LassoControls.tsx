// ── Free Select (Lasso) Tool Controls ────────────────────────────────────
import { useCanvasContext } from "../CanvasContext";

const rowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  padding: "4px 8px",
};

const labelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "rgba(255,255,255,0.7)",
  flex: 1,
  userSelect: "none",
};

const checkboxStyle: React.CSSProperties = {
  accentColor: "var(--bs-primary, #6399ff)",
  width: 14,
  height: 14,
  cursor: "pointer",
  flexShrink: 0,
};

const sliderStyle: React.CSSProperties = {
  flex: 1,
  minWidth: 0,
};

const numberStyle: React.CSSProperties = {
  width: 40,
  background: "rgba(0,0,0,0.4)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 4,
  color: "rgba(255,255,255,0.8)",
  fontSize: 11,
  textAlign: "center",
  padding: "2px 0",
  flexShrink: 0,
};

const dividerStyle: React.CSSProperties = {
  height: 1,
  background: "rgba(255,255,255,0.07)",
  margin: "2px 8px",
};

export default function LassoControls() {
  const canvas = useCanvasContext();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>

      {/* Antialiasing */}
      <label style={{ ...rowStyle, cursor: "pointer" }}>
        <input
          type="checkbox"
          style={checkboxStyle}
          checked={canvas.lassoAntialiasing}
          onChange={(e) => canvas.setLassoAntialiasing(e.target.checked)}
        />
        <span style={labelStyle}>Antialiasing</span>
      </label>

      <div style={dividerStyle} />

      {/* Feather edges */}
      <label style={{ ...rowStyle, cursor: "pointer" }}>
        <input
          type="checkbox"
          style={checkboxStyle}
          checked={canvas.lassoFeatherEdges}
          onChange={(e) => canvas.setLassoFeatherEdges(e.target.checked)}
        />
        <span style={labelStyle}>Feather edges</span>
      </label>

      {/* Feather radius — only visible when feather is on */}
      {canvas.lassoFeatherEdges && (
        <div
          style={{
            ...rowStyle,
            paddingTop: 2,
            opacity: canvas.lassoFeatherEdges ? 1 : 0.35,
            pointerEvents: canvas.lassoFeatherEdges ? "auto" : "none",
          }}
        >
          <span style={{ ...labelStyle, flex: "none", fontSize: 11, color: "rgba(255,255,255,0.45)" }}>
            Radius
          </span>
          <input
            type="range"
            min={0}
            max={100}
            step={0.5}
            value={canvas.lassoFeatherRadius}
            onChange={(e) => canvas.setLassoFeatherRadius(Number(e.target.value))}
            style={sliderStyle}
            title={`Feather radius: ${canvas.lassoFeatherRadius.toFixed(1)} px`}
          />
          <input
            type="number"
            value={canvas.lassoFeatherRadius}
            onChange={(e) => canvas.setLassoFeatherRadius(Number(e.target.value))}
            onBlur={(e) =>
              canvas.setLassoFeatherRadius(
                Math.max(0, Math.min(100, Number(e.target.value))),
              )
            }
            style={numberStyle}
          />
        </div>
      )}
    </div>
  );
}
