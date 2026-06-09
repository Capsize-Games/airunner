// ── Crop Tool Controls ──────────────────────────────────────────────────
// Two-way bound sliders for crop position (X/Y) and size (Width/Height).
// Changes here update the Konva crop rect in real time;
// Konva Transformer changes update these sliders in real time.

import { useCanvasContext } from "../CanvasContext";

const rowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  padding: "3px 8px",
};

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "rgba(255,255,255,0.5)",
  flex: "none",
  width: 42,
  userSelect: "none",
};

const sliderStyle: React.CSSProperties = {
  flex: 1,
  minWidth: 0,
};

const numberStyle: React.CSSProperties = {
  width: 48,
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

const sectionStyle: React.CSSProperties = {
  fontSize: 10,
  fontWeight: 600,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  color: "rgba(255,255,255,0.35)",
  padding: "6px 8px 2px 8px",
  userSelect: "none",
};

const hintStyle: React.CSSProperties = {
  fontSize: 10,
  color: "rgba(255,255,255,0.3)",
  padding: "4px 8px 8px 8px",
  userSelect: "none",
  lineHeight: 1.4,
};

export default function CropControls() {
  const canvas = useCanvasContext();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Position */}
      <div style={sectionStyle}>Position</div>

      <div style={rowStyle}>
        <span style={labelStyle}>X</span>
        <input
          type="range"
          min={0}
          max={canvas.documentWidth}
          step={1}
          value={canvas.cropX}
          onChange={(e) => canvas.setCropX(Number(e.target.value))}
          style={sliderStyle}
          title={`Crop X: ${canvas.cropX} px`}
        />
        <input
          type="number"
          min={0}
          max={canvas.documentWidth}
          step={1}
          value={canvas.cropX}
          onChange={(e) =>
            canvas.setCropX(
              Math.max(0, Math.min(canvas.documentWidth, Number(e.target.value))),
            )
          }
          style={numberStyle}
        />
      </div>

      <div style={rowStyle}>
        <span style={labelStyle}>Y</span>
        <input
          type="range"
          min={0}
          max={canvas.documentHeight}
          step={1}
          value={canvas.cropY}
          onChange={(e) => canvas.setCropY(Number(e.target.value))}
          style={sliderStyle}
          title={`Crop Y: ${canvas.cropY} px`}
        />
        <input
          type="number"
          min={0}
          max={canvas.documentHeight}
          step={1}
          value={canvas.cropY}
          onChange={(e) =>
            canvas.setCropY(
              Math.max(0, Math.min(canvas.documentHeight, Number(e.target.value))),
            )
          }
          style={numberStyle}
        />
      </div>

      <div style={dividerStyle} />

      {/* Size */}
      <div style={sectionStyle}>Size</div>

      <div style={rowStyle}>
        <span style={labelStyle}>W</span>
        <input
          type="range"
          min={1}
          max={canvas.documentWidth}
          step={1}
          value={canvas.cropWidth}
          onChange={(e) => canvas.setCropWidth(Number(e.target.value))}
          style={sliderStyle}
          title={`Crop width: ${canvas.cropWidth} px`}
        />
        <input
          type="number"
          min={1}
          max={canvas.documentWidth}
          step={1}
          value={canvas.cropWidth}
          onChange={(e) =>
            canvas.setCropWidth(
              Math.max(1, Math.min(canvas.documentWidth, Number(e.target.value))),
            )
          }
          style={numberStyle}
        />
      </div>

      <div style={rowStyle}>
        <span style={labelStyle}>H</span>
        <input
          type="range"
          min={1}
          max={canvas.documentHeight}
          step={1}
          value={canvas.cropHeight}
          onChange={(e) => canvas.setCropHeight(Number(e.target.value))}
          style={sliderStyle}
          title={`Crop height: ${canvas.cropHeight} px`}
        />
        <input
          type="number"
          min={1}
          max={canvas.documentHeight}
          step={1}
          value={canvas.cropHeight}
          onChange={(e) =>
            canvas.setCropHeight(
              Math.max(1, Math.min(canvas.documentHeight, Number(e.target.value))),
            )
          }
          style={numberStyle}
        />
      </div>

      <div style={dividerStyle} />

      <div style={hintStyle}>
        Draw a rectangle on the canvas, then drag handles to adjust.
        Press <b>Enter</b> to commit or <b>Esc</b> to cancel.
      </div>
    </div>
  );
}
