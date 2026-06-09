// ── Zoom Tool Controls ─────────────────────────────────────────────
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

const hintStyle: React.CSSProperties = {
  fontSize: 10,
  color: "rgba(255,255,255,0.3)",
  padding: "0 8px 8px 8px",
  userSelect: "none",
  lineHeight: 1.4,
};

export default function ZoomControls() {
  const canvas = useCanvasContext();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Direction — radio buttons */}
      <div style={sectionStyle}>
        <span style={labelStyle}>Direction</span>

        <label style={radioRowStyle}>
          <input
            type="radio"
            name="zoomDirection"
            style={radioInputStyle}
            checked={canvas.zoomDirection === "in"}
            onChange={() => canvas.setZoomDirection("in")}
          />
          <span style={radioLabelStyle}>Zoom In</span>
        </label>

        <label style={radioRowStyle}>
          <input
            type="radio"
            name="zoomDirection"
            style={radioInputStyle}
            checked={canvas.zoomDirection === "out"}
            onChange={() => canvas.setZoomDirection("out")}
          />
          <span style={radioLabelStyle}>Zoom Out</span>
        </label>
      </div>
      <div style={hintStyle}>
        Click to zoom centered on pointer.{'\n'}
        Drag to marquee-zoom a region.
      </div>
    </div>
  );
}
