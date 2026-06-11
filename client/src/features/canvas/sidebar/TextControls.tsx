// ── Text Tool Controls ─────────────────────────────────────────────────
// Font family dropdown, font size input, and color picker for the text
// tool.  Changes update global text settings and, if a text node is
// actively being edited, apply immediately to the active node.

import { useCanvasContext } from "../CanvasContext";

// ── Web-safe font stack ──────────────────────────────────────────────────

const FONTS = [
  "Arial",
  "Verdana",
  "Helvetica",
  "Tahoma",
  "Trebuchet MS",
  "Times New Roman",
  "Georgia",
  "Garamond",
  "Courier New",
  "Brush Script MT",
  "Impact",
  "Comic Sans MS",
];

// ── Styles ───────────────────────────────────────────────────────────────

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
  marginBottom: 2,
};

const selectStyle: React.CSSProperties = {
  width: "100%",
  padding: "3px 6px",
  fontSize: 12,
  background: "rgba(255,255,255,0.06)",
  color: "rgba(255,255,255,0.85)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 4,
  outline: "none",
  cursor: "pointer",
};

const inputRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
};

const numberInputStyle: React.CSSProperties = {
  width: 64,
  padding: "3px 6px",
  fontSize: 12,
  background: "rgba(255,255,255,0.06)",
  color: "rgba(255,255,255,0.85)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 4,
  outline: "none",
};

const colorInputStyle: React.CSSProperties = {
  width: 32,
  height: 26,
  padding: 0,
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 4,
  cursor: "pointer",
  background: "transparent",
};

const hintStyle: React.CSSProperties = {
  fontSize: 10,
  color: "rgba(255,255,255,0.3)",
  padding: "0 8px 8px 8px",
  userSelect: "none",
  lineHeight: 1.4,
};

// ── Component ────────────────────────────────────────────────────────────

export default function TextControls() {
  const canvas = useCanvasContext();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Font family */}
      <div style={sectionStyle}>
        <span style={labelStyle}>Font</span>
        <select
          style={selectStyle}
          value={canvas.textFont}
          onChange={(e) => canvas.setTextFont(e.target.value)}
        >
          {FONTS.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      </div>

      {/* Font size */}
      <div style={sectionStyle}>
        <span style={labelStyle}>Size</span>
        <div style={inputRowStyle}>
          <input
            type="number"
            style={numberInputStyle}
            value={canvas.textSize}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!isNaN(v)) canvas.setTextSize(v);
            }}
            onBlur={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!isNaN(v)) canvas.setTextSize(Math.max(1, v));
            }}
          />
          <span style={{ fontSize: 11, color: "rgba(255,255,255,0.35)" }}>
            px
          </span>
        </div>
      </div>

      {/* Color */}
      <div style={sectionStyle}>
        <span style={labelStyle}>Color</span>
        <div style={inputRowStyle}>
          <input
            type="color"
            style={colorInputStyle}
            value={canvas.textColor}
            onChange={(e) => canvas.setTextColor(e.target.value)}
          />
          <span style={{ fontSize: 11, color: "rgba(255,255,255,0.5)" }}>
            {canvas.textColor}
          </span>
        </div>
      </div>

      <div style={hintStyle}>
        Click anywhere on the canvas to place text. Type to edit,
        then click elsewhere to finish.
      </div>
    </div>
  );
}
