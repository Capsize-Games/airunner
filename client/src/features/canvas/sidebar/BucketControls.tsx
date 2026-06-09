// ── Bucket (Flood) Fill Tool Controls ──────────────────────────────────
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

const radioStyle: React.CSSProperties = {
  ...checkboxStyle,
  accentColor: "var(--bs-primary, #6399ff)",
};

const radioGroupStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 2,
  padding: "4px 8px 4px 28px",
};

const radioRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  cursor: "pointer",
};

const radioLabelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "rgba(255,255,255,0.6)",
  userSelect: "none",
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

export default function BucketControls() {
  const canvas = useCanvasContext();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Color source */}
      <div style={rowStyle}>
        <span style={labelStyle}>Color source</span>
      </div>
      <div style={radioGroupStyle}>
        <label style={radioRowStyle}>
          <input
            type="radio"
            name="bucketColorSource"
            style={radioStyle}
            checked={canvas.bucketColorSource === "foreground"}
            onChange={() =>
              canvas.setBucketColorSource("foreground")
            }
          />
          <span style={radioLabelStyle}>Foreground color</span>
        </label>
        <label style={radioRowStyle}>
          <input
            type="radio"
            name="bucketColorSource"
            style={radioStyle}
            checked={canvas.bucketColorSource === "background"}
            onChange={() =>
              canvas.setBucketColorSource("background")
            }
          />
          <span style={radioLabelStyle}>Background color</span>
        </label>
      </div>

      <div style={dividerStyle} />

      {/* Fill transparent areas */}
      <label style={{ ...rowStyle, cursor: "pointer" }}>
        <input
          type="checkbox"
          style={checkboxStyle}
          checked={canvas.bucketFillTransparentAreas}
          onChange={(e) =>
            canvas.setBucketFillTransparentAreas(e.target.checked)
          }
        />
        <span style={labelStyle}>Fill transparent areas</span>
      </label>

      <div style={dividerStyle} />

      {/* Antialiasing */}
      <label style={{ ...rowStyle, cursor: "pointer" }}>
        <input
          type="checkbox"
          style={checkboxStyle}
          checked={canvas.bucketAntialiasing}
          onChange={(e) =>
            canvas.setBucketAntialiasing(e.target.checked)
          }
        />
        <span style={labelStyle}>Antialiasing</span>
      </label>

      <div style={dividerStyle} />

      {/* Threshold */}
      <div style={{ ...rowStyle, paddingTop: 2 }}>
        <span
          style={{
            ...labelStyle,
            flex: "none",
            fontSize: 11,
            color: "rgba(255,255,255,0.45)",
          }}
        >
          Threshold
        </span>
        <input
          type="range"
          min={0}
          max={100}
          step={0.5}
          value={canvas.bucketThreshold}
          onChange={(e) =>
            canvas.setBucketThreshold(Number(e.target.value))
          }
          style={sliderStyle}
          title={`Threshold: ${canvas.bucketThreshold.toFixed(1)}`}
        />
        <input
          type="number"
          min={0}
          max={100}
          step={0.5}
          value={canvas.bucketThreshold}
          onChange={(e) =>
            canvas.setBucketThreshold(
              Math.max(0, Math.min(100, Number(e.target.value))),
            )
          }
          style={numberStyle}
        />
      </div>
    </div>
  );
}
