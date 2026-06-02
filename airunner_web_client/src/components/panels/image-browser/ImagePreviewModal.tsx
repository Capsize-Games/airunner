import { useEffect, useCallback } from "react";
import { BASE_URL } from "../../../types/api";
import type { ImageInfo } from "../../../api/client";
import { formatTimestamp, formatFileSize } from "./LocalImageHelpers";

const separatorColor = "rgba(255,255,255,0.15)";
const rowBorderColor = "rgba(255,255,255,0.08)";

function filterMetadata(
  img: ImageInfo,
): [string, unknown][] {
  const version = img.metadata?.version as string | undefined;
  const versionStr = typeof version === "string" ? version.toLowerCase() : "";
  const isSdxlVersion =
    versionStr.includes("sdxl") ||
    versionStr.includes("hyper") ||
    versionStr.includes("lightning");

  const hiddenKeys = [
    "prompt_2", "negative_prompt", "negative_prompt_2",
    "secondary_prompt", "secondary_negative_prompt",
  ];
  return img.metadata
    ? Object.entries(img.metadata).filter(([key]) => {
        if (!isSdxlVersion && hiddenKeys.includes(key)) {
          return false;
        }
        return true;
      })
    : [];
}

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
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowLeft") {
        onPrev();
      } else if (e.key === "ArrowRight") {
        onNext();
      }
    },
    [onClose, onPrev, onNext],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (currentIndex < 0 || currentIndex >= images.length) return null;

  const img = images[currentIndex];
  const metaEntries = filterMetadata(img);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.8)",
        zIndex: 1100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={onClose}
    >
      <div
        style={{
          position: "relative",
          display: "flex",
          gap: 16,
          padding: 12,
          paddingTop: 44,
          maxHeight: "85vh",
          maxWidth: "90vw",
          border: "1px solid rgba(255,255,255,0.2)",
          borderRadius: 4,
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          style={{
            position: "absolute",
            top: 8,
            right: 8,
            background: "rgba(0,0,0,0.5)",
            border: "1px solid rgba(255,255,255,0.3)",
            color: "#fff",
            fontSize: 18,
            cursor: "pointer",
            lineHeight: 1,
            width: 30,
            height: 30,
            borderRadius: 4,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title="Close (Esc)"
        >
          ✕
        </button>
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <img
            src={`${BASE_URL}${img.image_url}`}
            alt={img.id}
            style={{
              maxWidth: "100%",
              maxHeight: "80vh",
              objectFit: "contain",
            }}
          />
        </div>
        <div
          style={{
            width: 360,
            maxHeight: "80vh",
            display: "flex",
            flexDirection: "column",
            color: "#ccc",
          }}
        >
          <div style={{ marginBottom: 8, flexShrink: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: "#fff" }}>
              {img.id}
            </div>
            <div style={{ fontSize: 11, color: "#aaa", marginTop: 2 }}>
              {formatTimestamp(img.file_timestamp)}
              {" · "}
              {formatFileSize(img.file_size)}
            </div>
          </div>
          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
            {metaEntries.length > 0 ? (
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 12,
                }}
              >
                <thead>
                  <tr style={{ background: "rgba(255,255,255,0.06)" }}>
                    <th
                      style={{
                        padding: "3px 8px 3px 0",
                        textAlign: "left",
                        fontSize: 10,
                        textTransform: "uppercase",
                        letterSpacing: 0.5,
                        color: "#aaa",
                        fontWeight: 600,
                        borderBottom: `1px solid ${separatorColor}`,
                      }}
                    >
                      Metadata
                    </th>
                    <th
                      style={{
                        padding: "3px 0",
                        textAlign: "left",
                        fontSize: 10,
                        textTransform: "uppercase",
                        letterSpacing: 0.5,
                        color: "#aaa",
                        fontWeight: 600,
                        borderBottom: `1px solid ${separatorColor}`,
                      }}
                    />
                  </tr>
                </thead>
                <tbody>
                  {metaEntries.map(([key, value], idx) => {
                    const valStr =
                      typeof value === "object"
                        ? JSON.stringify(value)
                        : String(value);
                    return (
                      <tr
                        key={key}
                        style={{
                          background:
                            idx % 2 === 0
                              ? "rgba(255,255,255,0.03)"
                              : "transparent",
                        }}
                      >
                        <td
                          style={{
                            padding: "2px 8px 2px 0",
                            verticalAlign: "top",
                            whiteSpace: "nowrap",
                            color: "#aaa",
                            fontWeight: 600,
                            width: 1,
                            borderBottom: `1px solid ${rowBorderColor}`,
                          }}
                        >
                          {key}
                        </td>
                        <td
                          style={{
                            padding: "2px 0",
                            verticalAlign: "top",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            maxWidth: 0,
                            borderBottom: `1px solid ${rowBorderColor}`,
                          }}
                          title={valStr}
                        >
                          {valStr.length > 120
                            ? valStr.slice(0, 120) + "..."
                            : valStr}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <p
                style={{
                  color: "#888",
                  fontSize: 12,
                  textAlign: "center",
                }}
              >
                No metadata
              </p>
            )}
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: 16,
              gap: 8,
              alignItems: "center",
              flexShrink: 0,
            }}
          >
            <button
              onClick={onPrev}
              disabled={currentIndex <= 0}
              style={{
                flex: 1,
                padding: "6px 12px",
                background:
                  currentIndex <= 0
                    ? "rgba(255,255,255,0.1)"
                    : "rgba(255,255,255,0.2)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: 4,
                color: currentIndex <= 0 ? "#666" : "#fff",
                cursor: currentIndex <= 0 ? "default" : "pointer",
                fontSize: 13,
              }}
            >
              ◀ Previous
            </button>
            <span
              style={{
                color: "#aaa",
                fontSize: 12,
                whiteSpace: "nowrap",
              }}
            >
              {currentIndex + 1} / {images.length}
            </span>
            <button
              onClick={onNext}
              disabled={currentIndex >= images.length - 1}
              style={{
                flex: 1,
                padding: "6px 12px",
                background:
                  currentIndex >= images.length - 1
                    ? "rgba(255,255,255,0.1)"
                    : "rgba(255,255,255,0.2)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: 4,
                color:
                  currentIndex >= images.length - 1 ? "#666" : "#fff",
                cursor:
                  currentIndex >= images.length - 1
                    ? "default"
                    : "pointer",
                fontSize: 13,
              }}
            >
              Next ▶
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
