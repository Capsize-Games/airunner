import { useState, useEffect, useCallback } from "react";
import { BASE_URL } from "../../types/api";

const CANVAS_IMAGE_URL = "/api/v1/canvas/image";

export default function CanvasPanel() {
  const [loading, setLoading] = useState(true);
  const [hasImage, setHasImage] = useState(false);
  const [droppedUrl, setDroppedUrl] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch(CANVAS_IMAGE_URL)
      .then((r) => {
        setHasImage(r.ok);
        setLoading(false);
      })
      .catch(() => {
        setHasImage(false);
        setLoading(false);
      });
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const url = e.dataTransfer.getData("text/image-url");
    if (url) {
      setDroppedUrl(url);
    }
  }, []);

  if (loading) {
    return (
      <div className="canvas-panel d-flex align-items-center justify-content-center h-100">
        <div
          className="spinner-border spinner-border-sm"
          role="status"
          style={{ color: "var(--theme-text-secondary)" }}
        />
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
          <small style={{ color: "var(--theme-text-secondary)" }}>
            No image on canvas. Generate one to see it here.
          </small>
        </div>
      </div>
    );
  }

  const displayUrl = droppedUrl || CANVAS_IMAGE_URL;

  return (
    <div
      className="canvas-panel d-flex align-items-center justify-content-center h-100 overflow-hidden"
      style={{ background: "var(--theme-bg)" }}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <img
        src={displayUrl}
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
