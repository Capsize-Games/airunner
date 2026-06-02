import { useState, useEffect } from "react";

const IMAGE_URL = "/api/v1/canvas/image";

export default function CanvasPanel() {
  const [loading, setLoading] = useState(true);
  const [hasImage, setHasImage] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(IMAGE_URL)
      .then((r) => {
        setHasImage(r.ok);
        setLoading(false);
      })
      .catch(() => {
        setHasImage(false);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="canvas-panel d-flex align-items-center justify-content-center h-100">
        <small style={{ color: "#a0a0a8" }}>Loading...</small>
      </div>
    );
  }

  if (!hasImage) {
    return (
      <div className="canvas-panel d-flex align-items-center justify-content-center h-100">
        <div className="text-center">
          <span
            className="d-block mb-2"
            style={{ fontSize: "3rem", opacity: 0.3 }}
          >
            🎨
          </span>
          <small style={{ color: "#a0a0a8" }}>
            No image on canvas. Generate one to see it here.
          </small>
        </div>
      </div>
    );
  }

  return (
    <div
      className="canvas-panel d-flex align-items-center justify-content-center h-100 overflow-hidden"
      style={{ background: "#111" }}
    >
      <img
        src={IMAGE_URL}
        alt="Canvas"
        style={{
          maxWidth: "100%",
          maxHeight: "100%",
          objectFit: "contain",
        }}
      />
    </div>
  );
}
