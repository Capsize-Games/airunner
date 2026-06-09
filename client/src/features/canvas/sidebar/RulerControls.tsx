// ── Ruler Tool Controls ───────────────────────────────────────────
import { useCanvasContext } from "../CanvasContext";

const rowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  padding: "5px 8px",
};

export default function RulerControls() {
  const canvas = useCanvasContext();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      <div style={rowStyle}>
        <label style={{
          display: "flex", alignItems: "center", gap: 6,
          cursor: "pointer", userSelect: "none",
        }}>
          <input
            type="checkbox"
            checked={canvas.rulerShowRuler}
            onChange={(e) => canvas.setRulerShowRuler(e.target.checked)}
            style={{ margin: 0, cursor: "pointer", accentColor: "#6fa8ff" }}
          />
          <span style={{ fontSize: 11, color: "rgba(255,255,255,0.7)" }}>
            Show Ruler
          </span>
        </label>
      </div>
    </div>
  );
}
