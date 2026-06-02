export default function CanvasPanel() {
  return (
    <div
      className="canvas-panel d-flex align-items-center justify-content-center"
      style={{ background: "#111" }}
    >
      <div className="text-center">
        <span
          className="d-block mb-2"
          style={{ fontSize: "3rem", opacity: 0.3 }}
        >
          🎨
        </span>
        <span className="text-muted small">
          Canvas area — drag and drop images here, or use
          the image generation tools.
        </span>
      </div>
    </div>
  );
}
