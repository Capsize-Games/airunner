// ── Pipette (Color Picker) Tool Controls ──────────────────────────────
import { useCanvasContext } from "../CanvasContext";

const sectionStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 4,
  padding: "6px 8px",
};

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "rgba(255,255,255,0.6)",
  userSelect: "none",
  marginBottom: 4,
};

const radioRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  padding: "2px 0",
};

const radioLabelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "rgba(255,255,255,0.7)",
  userSelect: "none",
  cursor: "pointer",
};

const radioInputStyle: React.CSSProperties = {
  margin: 0,
  cursor: "pointer",
  accentColor: "#6fa8ff",
};

const swatchRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "4px 0",
};

const swatchStyle = (color: string): React.CSSProperties => ({
  width: 24,
  height: 24,
  borderRadius: 4,
  background: color,
  border: "1.5px solid rgba(255,255,255,0.15)",
  flexShrink: 0,
});

const swatchLabelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "rgba(255,255,255,0.45)",
  userSelect: "none",
};

const hintStyle: React.CSSProperties = {
  fontSize: 10,
  color: "rgba(255,255,255,0.3)",
  padding: "0 8px 8px 8px",
  userSelect: "none",
  lineHeight: 1.4,
};

export default function PipetteControls() {
  const canvas = useCanvasContext();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Target routing — radio buttons */}
      <div style={sectionStyle}>
        <span style={labelStyle}>Target</span>

        <label style={radioRowStyle}>
          <input
            type="radio"
            name="pipetteTarget"
            style={radioInputStyle}
            checked={canvas.pipetteTarget === "foreground"}
            onChange={() => canvas.setPipetteTarget("foreground")}
          />
          <span style={radioLabelStyle}>Set Foreground Color</span>
        </label>

        <label style={radioRowStyle}>
          <input
            type="radio"
            name="pipetteTarget"
            style={radioInputStyle}
            checked={canvas.pipetteTarget === "background"}
            onChange={() => canvas.setPipetteTarget("background")}
          />
          <span style={radioLabelStyle}>Set Background Color</span>
        </label>
      </div>

      {/* Current color swatches */}
      <div style={sectionStyle}>
        <span style={labelStyle}>Current Colors</span>
        <div style={swatchRowStyle}>
          <div style={swatchStyle(canvas.brushColor)} title={canvas.brushColor} />
          <span style={swatchLabelStyle}>
            Foreground: <strong>{canvas.brushColor}</strong>
          </span>
        </div>
        <div style={swatchRowStyle}>
          <div style={swatchStyle(canvas.documentBgColor)}
            title={canvas.documentBgColor}
          />
          <span style={swatchLabelStyle}>
            Background: <strong>{canvas.documentBgColor}</strong>
          </span>
        </div>
      </div>

      <div style={hintStyle}>
        Click anywhere on the canvas to sample the exact pixel color
        under the cursor.
      </div>
    </div>
  );
}
