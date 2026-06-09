// ── Move Tool Controls ──────────────────────────────────────────────
import { useCanvasContext } from "../CanvasContext";
import type { MoveMode } from "../canvasTypes";

const radioStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  padding: "4px 6px",
  cursor: "pointer",
  fontSize: 12,
  color: "rgba(255,255,255,0.7)",
  borderRadius: 4,
  transition: "background 0.1s",
  border: "none",
  background: "transparent",
  width: "100%",
  textAlign: "left",
};

const radioDotStyle = (active: boolean): React.CSSProperties => ({
  width: 12,
  height: 12,
  borderRadius: "50%",
  border: active ? "4px solid var(--bs-primary)" : "2px solid rgba(255,255,255,0.3)",
  background: active ? "var(--bs-primary)" : "transparent",
  flexShrink: 0,
  transition: "border 0.1s, background 0.1s",
});

const OPTIONS: { value: MoveMode; label: string }[] = [
  { value: "pick",          label: "Pick a layer or guide" },
  { value: "move-selected", label: "Move the selected layers" },
];

export default function MoveControls() {
  const canvas = useCanvasContext();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        padding: "6px 8px",
      }}
    >
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => canvas.setMoveMode(opt.value)}
          style={{
            ...radioStyle,
            background:
              canvas.moveMode === opt.value
                ? "rgba(99,153,255,0.12)"
                : "transparent",
          }}
          onMouseEnter={(e) => {
            if (canvas.moveMode !== opt.value) {
              e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            }
          }}
          onMouseLeave={(e) => {
            if (canvas.moveMode !== opt.value) {
              e.currentTarget.style.background = "transparent";
            }
          }}
        >
          <div style={radioDotStyle(canvas.moveMode === opt.value)} />
          {opt.label}
        </button>
      ))}
    </div>
  );
}
