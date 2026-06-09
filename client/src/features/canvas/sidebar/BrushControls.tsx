import { useRef } from "react";
import { useCanvasContext } from "../CanvasContext";

export default function BrushControls() {
  const canvas = useCanvasContext();
  const colorInputRef = useRef<HTMLInputElement>(null);
  const brushActive = canvas.activeTool === "brush" || canvas.activeTool === "eraser";

  return (
    <div
      className="d-flex align-items-center flex-shrink-0 border-b-subtle"
      style={{
        gap: 6, padding: "5px 8px",
        opacity: brushActive ? 1 : 0.35,
        pointerEvents: brushActive ? "auto" : "none",
      }}
    >
      <label title="Brush color" className="cursor-pointer flex-shrink-0 position-relative">
        <div style={{
          width: 20, height: 20, borderRadius: 4,
          background: canvas.brushColor,
          border: "2px solid rgba(255,255,255,0.2)", cursor: "pointer",
        }} />
        <input
          ref={colorInputRef}
          type="color"
          value={canvas.brushColor}
          onChange={(e) => canvas.setBrushColor(e.target.value)}
          style={{ position: "absolute", opacity: 0, width: 1, height: 1, pointerEvents: "none" }}
          tabIndex={-1}
        />
      </label>

      <input
        type="range" min={1} max={200} step={1}
        value={canvas.brushSize}
        onChange={(e) => canvas.setBrushSize(Number(e.target.value))}
        className="flex-grow-1 min-w-0"
        title={`Brush size: ${canvas.brushSize}px`}
      />

      <input
        type="number" min={1} max={200}
        value={canvas.brushSize}
        onChange={(e) => canvas.setBrushSize(Math.max(1, Math.min(200, Number(e.target.value))))}
        style={{
          width: 38, background: "rgba(0,0,0,0.4)",
          border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4,
          color: "rgba(255,255,255,0.8)", fontSize: 11,
          textAlign: "center", padding: "2px 0", flexShrink: 0,
        }}
      />
    </div>
  );
}
