// ── Smudge Tool Controls ────────────────────────────────────────────────
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

const hintStyle: React.CSSProperties = {
  fontSize: 10,
  color: "rgba(255,255,255,0.3)",
  padding: "4px 8px 8px 8px",
  userSelect: "none",
  lineHeight: 1.4,
};

export default function SmudgeControls() {
  const canvas = useCanvasContext();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Brush size */}
      <div style={{ ...rowStyle, paddingTop: 2 }}>
        <span
          style={{
            ...labelStyle,
            flex: "none",
            fontSize: 11,
            color: "rgba(255,255,255,0.45)",
          }}
        >
          Size
        </span>
        <input
          type="range"
          min={0}
          max={100}
          step={0.5}
          value={canvas.smudgeSize}
          onChange={(e) =>
            canvas.setSmudgeSize(Number(e.target.value))
          }
          style={sliderStyle}
          title={`Smudge size: ${canvas.smudgeSize.toFixed(1)}`}
        />
        <input
          type="number"
          value={canvas.smudgeSize}
          onChange={(e) => canvas.setSmudgeSize(Number(e.target.value))}
          onBlur={(e) =>
            canvas.setSmudgeSize(
              Math.max(0, Math.min(100, Number(e.target.value))),
            )
          }
          style={numberStyle}
        />
      </div>

      <div style={hintStyle}>
        Click and drag over an image to smear pixels along
        your stroke path.
      </div>
    </div>
  );
}
