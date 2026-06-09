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
      className="image-preview-backdrop"
      onClick={onClose}
    >
      <div
        className="image-preview-container"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="image-preview-close"
          title="Close (Esc)"
        >
          ✕
        </button>

        <div className="flex-grow-1 d-flex align-items-center justify-content-center">
          <img src={imageBlobUrl ?? undefined} alt={currentImg.id} style={{ maxWidth: "100%", maxHeight: "80vh", objectFit: "contain" }} />
        </div>

        <div className="d-flex flex-column flex-shrink-0" style={{ width: 360, maxHeight: "80vh", color: "#ccc" }}>
          <div className="flex-shrink-0" style={{ marginBottom: 8 }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: "#fff" }}>{currentImg.id}</div>
            <div style={{ fontSize: 11, color: "#aaa", marginTop: 2 }}>
              {formatTimestamp(currentImg.file_timestamp)} · {formatFileSize(currentImg.file_size)}
            </div>
          </div>

          <div className="scroll-panel">
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
