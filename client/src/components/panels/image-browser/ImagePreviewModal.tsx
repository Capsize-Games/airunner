import { useEffect, useCallback } from "react";
import type { ImageInfo } from "../../../api/client";
import { formatTimestamp, formatFileSize } from "./LocalImageHelpers";
import { useAuthenticatedBlobUrl } from "../../../hooks/useAuthenticatedBlobUrl";
import MetadataTable from "./MetadataTable";
import ModalNavigation from "./ModalNavigation";

export default function ImagePreviewModal({
  images,
  currentIndex,
  onClose,
  onPrev,
  onNext,
}: {
  images: ImageInfo[];
  currentIndex: number;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
}) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose();
    else if (e.key === "ArrowLeft") onPrev();
    else if (e.key === "ArrowRight") onNext();
  }, [onClose, onPrev, onNext]);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const currentImg = currentIndex >= 0 && currentIndex < images.length ? images[currentIndex] : null;
  const imageBlobUrl = useAuthenticatedBlobUrl(currentImg?.image_url ?? null);

  if (!currentImg) return null;

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", zIndex: 1100, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={onClose}
    >
      <div
        style={{ position: "relative", display: "flex", gap: 16, padding: 12, paddingTop: 44, maxHeight: "85vh", maxWidth: "90vw", border: "1px solid rgba(255,255,255,0.2)", borderRadius: 4, overflow: "hidden" }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          style={{ position: "absolute", top: 8, right: 8, background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.3)", color: "#fff", fontSize: 18, cursor: "pointer", lineHeight: 1, width: 30, height: 30, borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center" }}
          title="Close (Esc)"
        >
          ✕
        </button>

        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <img src={imageBlobUrl ?? undefined} alt={currentImg.id} style={{ maxWidth: "100%", maxHeight: "80vh", objectFit: "contain" }} />
        </div>

        <div style={{ width: 360, maxHeight: "80vh", display: "flex", flexDirection: "column", color: "#ccc" }}>
          <div style={{ marginBottom: 8, flexShrink: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: "#fff" }}>{currentImg.id}</div>
            <div style={{ fontSize: 11, color: "#aaa", marginTop: 2 }}>
              {formatTimestamp(currentImg.file_timestamp)} · {formatFileSize(currentImg.file_size)}
            </div>
          </div>

          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
            <MetadataTable img={currentImg} />
          </div>

          <ModalNavigation
            currentIndex={currentIndex}
            total={images.length}
            onPrev={onPrev}
            onNext={onNext}
          />
        </div>
      </div>
    </div>
  );
}
