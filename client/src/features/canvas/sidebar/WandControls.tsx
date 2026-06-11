// ── Fuzzy Select (Magic Wand) Tool Controls ──────────────────────────────
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

export default function WandControls() {
  const canvas = useCanvasContext();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>

      {/* Antialiasing */}
      <label style={{ ...rowStyle, cursor: "pointer" }}>
        <input
          type="checkbox"
          style={checkboxStyle}
          checked={canvas.wandAntialiasing}
          onChange={(e) => canvas.setWandAntialiasing(e.target.checked)}
        />
        <span style={labelStyle}>Antialiasing</span>
      </label>

      <div style={dividerStyle} />

      {/* Feather edges */}
      <label style={{ ...rowStyle, cursor: "pointer" }}>
        <input
          type="checkbox"
          style={checkboxStyle}
          checked={canvas.wandFeatherEdges}
          onChange={(e) => canvas.setWandFeatherEdges(e.target.checked)}
        />
        <span style={labelStyle}>Feather edges</span>
      </label>

      {/* Feather radius — only visible when feather is on */}
      {canvas.wandFeatherEdges && (
        <div
          style={{
            ...rowStyle,
            paddingTop: 2,
            opacity: canvas.wandFeatherEdges ? 1 : 0.35,
            pointerEvents: canvas.wandFeatherEdges ? "auto" : "none",
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
            value={canvas.wandFeatherRadius}
            onChange={(e) => canvas.setWandFeatherRadius(Number(e.target.value))}
            style={sliderStyle}
            title={`Feather radius: ${canvas.wandFeatherRadius.toFixed(1)} px`}
          />
          <input
            type="number"
            value={canvas.wandFeatherRadius}
            onChange={(e) => canvas.setWandFeatherRadius(Number(e.target.value))}
            onBlur={(e) =>
              canvas.setWandFeatherRadius(
                Math.max(0, Math.min(100, Number(e.target.value))),
              )
            }
            style={numberStyle}
          />
        </div>
      )}

      <div style={dividerStyle} />

      {/* Select transparent areas */}
      <label style={{ ...rowStyle, cursor: "pointer" }}>
        <input
          type="checkbox"
          style={checkboxStyle}
          checked={canvas.wandSelectTransparentAreas}
          onChange={(e) => canvas.setWandSelectTransparentAreas(e.target.checked)}
        />
        <span style={labelStyle}>Select transparent areas</span>
      </label>

      <div style={dividerStyle} />

      {/* Sample merged */}
      <label style={{ ...rowStyle, cursor: "pointer" }}>
        <input
          type="checkbox"
          style={checkboxStyle}
          checked={canvas.wandSampleMerged}
          onChange={(e) => canvas.setWandSampleMerged(e.target.checked)}
        />
        <span style={labelStyle}>Sample merged</span>
      </label>

      <div style={dividerStyle} />

      {/* Diagonal neighbors */}
      <label style={{ ...rowStyle, cursor: "pointer" }}>
        <input
          type="checkbox"
          style={checkboxStyle}
          checked={canvas.wandDiagonalNeighbors}
          onChange={(e) => canvas.setWandDiagonalNeighbors(e.target.checked)}
        />
        <span style={labelStyle}>Diagonal neighbors</span>
      </label>

      <div style={dividerStyle} />

      {/* Threshold */}
      <div style={{ ...rowStyle, paddingTop: 2 }}>
        <span style={{ ...labelStyle, flex: "none", fontSize: 11, color: "rgba(255,255,255,0.45)" }}>
          Threshold
        </span>
        <input
          type="range"
          min={0}
          max={100}
          step={0.5}
          value={canvas.wandThreshold}
          onChange={(e) => canvas.setWandThreshold(Number(e.target.value))}
          style={sliderStyle}
          title={`Threshold: ${canvas.wandThreshold.toFixed(1)}`}
        />
        <input
          type="number"
          value={canvas.wandThreshold}
          onChange={(e) => canvas.setWandThreshold(Number(e.target.value))}
          onBlur={(e) =>
            canvas.setWandThreshold(
              Math.max(0, Math.min(100, Number(e.target.value))),
            )
          }
          style={numberStyle}
        />
      </div>

    </div>
  );
}
