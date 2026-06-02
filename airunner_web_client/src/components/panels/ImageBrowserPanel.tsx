import { useState, useEffect, useRef, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
import Button from "react-bootstrap/Button";
import { BASE_URL } from "../../types/api";
import type { ImageDateInfo, ImageInfo } from "../../api/client";
import { deleteImage, renameImage } from "../../api/client";

const PAGE_SIZE = 20;
const LS_DATE_KEY = "airunner_image_browser_date";
const LS_LOCAL_IMAGES_KEY = "airunner_local_images";

// ── Local storage image helpers ────────────────────────────────────────────

interface LocalImageEntry {
  id: string;
  dataUrl: string;
  timestamp: string;
  prompt?: string;
  seed?: number;
  steps?: number;
  fileSize: number;
}

function getLocalImages(): LocalImageEntry[] {
  try {
    const raw = localStorage.getItem(LS_LOCAL_IMAGES_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as LocalImageEntry[];
  } catch {
    return [];
  }
}

function saveLocalImage(entry: LocalImageEntry): void {
  try {
    const existing = getLocalImages();
    existing.unshift(entry);
    // Keep max 100 local images
    const trimmed = existing.slice(0, 100);
    localStorage.setItem(LS_LOCAL_IMAGES_KEY, JSON.stringify(trimmed));
  } catch {
    // localStorage may be full
  }
}

function deleteLocalImage(id: string): void {
  try {
    const existing = getLocalImages().filter((e) => e.id !== id);
    localStorage.setItem(LS_LOCAL_IMAGES_KEY, JSON.stringify(existing));
  } catch {
    // ignore
  }
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const val = bytes / Math.pow(1024, i);
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatTimestamp(ts: number): string {
  try {
    const d = new Date(ts * 1000);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hours = String(d.getHours()).padStart(2, "0");
    const mins = String(d.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${mins}`;
  } catch {
    return "";
  }
}

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen) + "...";
}

// ── Image Preview Modal ─────────────────────────────────────────────────

function ImagePreviewModal({
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

  // Determine if version is SDXL-based (supports secondary/negative prompts)
  // or Z-Image (only single prompt - hide secondary/negative fields)
  const version = img.metadata?.version as string | undefined;
  const versionStr = typeof version === "string" ? version.toLowerCase() : "";
  const isSdxlVersion =
    versionStr.includes("sdxl") ||
    versionStr.includes("hyper") ||
    versionStr.includes("lightning");

  // Only show secondary/negative prompts for SDXL-based versions
  const hiddenKeys = [
    "prompt_2", "negative_prompt", "negative_prompt_2",
    "secondary_prompt", "secondary_negative_prompt",
  ];
  const metaEntries = img.metadata
    ? Object.entries(img.metadata).filter(([key]) => {
        if (!isSdxlVersion && hiddenKeys.includes(key)) {
          return false;
        }
        return true;
      })
    : [];

  const separatorColor = "rgba(255,255,255,0.15)";
  const rowBorderColor = "rgba(255,255,255,0.08)";

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
      {/* Close button floating outside */}
      <button
        onClick={onClose}
        style={{
          position: "fixed",
          top: 16,
          right: 16,
          background: "none",
          border: "none",
          color: "#fff",
          fontSize: 28,
          cursor: "pointer",
          lineHeight: 1,
          zIndex: 1110,
        }}
        title="Close (Esc)"
      >
        ✕
      </button>
      <div
        style={{
          display: "flex",
          gap: 0,
          maxHeight: "85vh",
          maxWidth: "90vw",
          border: "1px solid rgba(255,255,255,0.2)",
          borderRadius: 8,
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Left: full-size image */}
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

        {/* Right: metadata + navigation */}
        <div
          style={{
            width: 360,
            maxHeight: "80vh",
            display: "flex",
            flexDirection: "column",
            color: "#ccc",
          }}
        >
          {/* File info header */}
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

          {/* Metadata table — scrollable */}
          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
          {/* Metadata table */}
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

          {/* Previous / Next navigation — pinned to bottom */}
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

// ── Component ──────────────────────────────────────────────────────────────

export default function ImageBrowserPanel() {
  const [dates, setDates] = useState<ImageDateInfo[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(() => {
    try {
      return localStorage.getItem(LS_DATE_KEY);
    } catch {
      return null;
    }
  });
  const [serverImages, setServerImages] = useState<ImageInfo[]>([]);
  const [localImages, setLocalImages] = useState<LocalImageEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loadingDates, setLoadingDates] = useState(true);
  const [loadingImages, setLoadingImages] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [showLocal, setShowLocal] = useState(false);
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [moveFeedback, setMoveFeedback] = useState<string | null>(null);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);

  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // ── Load local images ──────────────────────────────────────────────────

  useEffect(() => {
    setLocalImages(getLocalImages());
  }, []);

  // ── Load dates on mount ─────────────────────────────────────────────

  const loadDates = useCallback(async () => {
    try {
      const { listImageDates } = await import("../../api/client");
      const data = await listImageDates();
      setDates(data.dates);
      if (data.dates.length > 0 && !selectedDate) {
        setSelectedDate(data.dates[0].value);
      } else if (selectedDate) {
        const stillExists = data.dates.some(
          (d) => d.value === selectedDate,
        );
        if (!stillExists && data.dates.length > 0) {
          setSelectedDate(data.dates[0].value);
        }
      }
    } catch {
      // unavailable
    } finally {
      setLoadingDates(false);
    }
  }, [selectedDate]);

  useEffect(() => {
    loadDates();
  }, [loadDates]);

  // ── Load server images for the selected date ─────────────────────────

  const loadImages = useCallback(
    async (date: string, currentOffset: number, append: boolean) => {
      setLoadingImages(true);
      try {
        const { listImages } = await import("../../api/client");
        const data = await listImages(date, currentOffset, PAGE_SIZE);
        if (append) {
          setServerImages((prev) => [...prev, ...data.images]);
        } else {
          setServerImages(data.images);
        }
        setTotal(data.total);
        setHasMore(currentOffset + PAGE_SIZE < data.total);
        setOffset(currentOffset + PAGE_SIZE);
        // Close any open preview when images reset
        setPreviewIndex(null);
      } catch {
        // unavailable
      } finally {
        setLoadingImages(false);
      }
    },
    [],
  );

  // Reset when the selected date changes
  useEffect(() => {
    if (!selectedDate) return;
    setServerImages([]);
    setOffset(0);
    setHasMore(true);
    loadImages(selectedDate, 0, false);
  }, [selectedDate, loadImages]);

  // ── Lazy loading via IntersectionObserver ───────────────────────────

  useEffect(() => {
    if (!hasMore || loadingImages || !sentinelRef.current) return;

    const sentinel = sentinelRef.current;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && selectedDate) {
          loadImages(selectedDate, offset, true);
        }
      },
      { rootMargin: "200px" },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loadingImages, selectedDate, offset, loadImages]);

  // ── SSE subscription for live reload ────────────────────────────────

  useEffect(() => {
    const eventSource = new EventSource(
      `${BASE_URL}/api/v1/art/images/watch`,
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "reload") {
          loadDates();
          setServerImages([]);
          setOffset(0);
          setHasMore(true);
          if (selectedDate) {
            loadImages(selectedDate, 0, false);
          }
          // Refresh local images too
          setLocalImages(getLocalImages());
        }
      } catch {
        // ignore malformed events
      }
    };

    eventSource.onerror = () => {
      // The browser will auto-reconnect
    };

    return () => {
      eventSource.close();
    };
  }, [loadDates, selectedDate, loadImages]);

  // ── Handle date selection ───────────────────────────────────────────

  const handleDateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value || null;
    if (val === "__local__") {
      setShowLocal(true);
      return;
    }
    setShowLocal(false);
    setSelectedDate(val);
    if (val) {
      try {
        localStorage.setItem(LS_DATE_KEY, val);
      } catch {}
    } else {
      try {
        localStorage.removeItem(LS_DATE_KEY);
      } catch {}
    }
  };

  // ── Rename handler ─────────────────────────────────────────────────

  const handleStartRename = (img: ImageInfo) => {
    setEditingId(img.id);
    setEditValue(img.id);
  };

  const handleCommitRename = async (date: string, oldId: string) => {
    const newName = editValue.trim();
    if (!newName || newName === oldId) {
      setEditingId(null);
      return;
    }
    setEditingId(null);
    try {
      const result = await renameImage(date, oldId, newName);
      setServerImages((prev) =>
        prev.map((img) =>
          img.id === oldId ? { ...img, id: result.new_id } : img,
        ),
      );
    } catch {
      // revert — keep old id
    }
  };

  const handleCancelRename = () => {
    setEditingId(null);
  };

  // ── Delete server image ────────────────────────────────────────────

  const executeDelete = async (date: string, filename: string) => {
    try {
      await deleteImage(date, filename);
      setServerImages((prev) => prev.filter((img) => img.id !== filename));
      setConfirmDeleteId(null);
    } catch {
      // delete failed
    }
  };

  const executeDeleteAll = async () => {
    if (!selectedDate) return;
    setConfirmDeleteAll(false);
    const current = serverImages;
    for (const img of current) {
      try {
        await deleteImage(selectedDate, img.id);
      } catch {
        // continue with remaining
      }
    }
    setServerImages([]);
    setTotal(0);
    setHasMore(false);
  };

  // ── Move to canvas ─────────────────────────────────────────────────

  const handleMoveToCanvas = async (img: ImageInfo) => {
    try {
      const url = `/api/v1/canvas/image?image_url=${encodeURIComponent(img.image_url)}`;
      await fetch(url, { method: "PUT" });
      setMoveFeedback(img.id);
      setTimeout(() => setMoveFeedback(prev => prev === img.id ? null : prev), 1500);
      window.dispatchEvent(new CustomEvent("canvas-image-changed"));
    } catch {
      // canvas move failed
    }
  };

  // ── Delete local image ──────────────────────────────────────────────

  const handleDeleteLocal = (id: string) => {
    deleteLocalImage(id);
    setLocalImages(getLocalImages());
  };

  // ── Modal navigation callbacks ──────────────────────────────────────

  const handlePrev = useCallback(() => {
    setPreviewIndex((prev) => {
      if (prev === null || prev <= 0) return prev;
      return prev - 1;
    });
  }, []);

  const handleNext = useCallback(() => {
    setPreviewIndex((prev) => {
      if (prev === null) return prev;
      return Math.min(prev + 1, serverImages.length - 1);
    });
  }, [serverImages.length]);

  // ── Render one server image row ────────────────────────────────────

  const renderServerRow = (img: ImageInfo, idx: number) => {
    const isEditing = editingId === img.id;
    const imgFilter = "var(--theme-icon-filter)";
    return (
      <div
        key={img.id}
        className="d-flex border rounded p-1 mb-1"
        style={{
          backgroundColor: "rgba(255,255,255,0.02)",
          minHeight: 98,
        }}
      >
        {/* Thumbnail */}
        <div
          className="border rounded overflow-hidden flex-shrink-0 align-self-start"
          style={{ width: 96, height: 96, cursor: "pointer" }}
          title={`Click to preview: ${img.id}`}
          onClick={() => setPreviewIndex(idx)}
          draggable
          onDragStart={(e) => {
            e.dataTransfer.setData(
              "text/image-url",
              `${BASE_URL}${img.image_url}`,
            );
            e.dataTransfer.effectAllowed = "copy";
          }}
        >
          <img
            src={`${BASE_URL}${img.thumbnail_url}`}
            alt={img.id}
            className="w-100 h-100"
            style={{ objectFit: "cover" }}
            loading="lazy"
          />
        </div>

        {/* Info */}
        <div className="ms-2 flex-grow-1 overflow-hidden d-flex flex-column"
          style={{ minWidth: 0 }}>
          {/* Row 1: click-to-edit filename + file_size */}
          <div className="d-flex justify-content-between align-items-start">
            {isEditing ? (
              <input
                type="text"
                className="form-control form-control-sm"
                style={{
                  fontSize: 12,
                  width: "100%",
                  minWidth: 0,
                }}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleCommitRename(selectedDate ?? "", img.id);
                  } else if (e.key === "Escape") {
                    handleCancelRename();
                  }
                }}
                onBlur={() =>
                  handleCommitRename(selectedDate ?? "", img.id)
                }
                autoFocus
              />
            ) : (
              <strong
                className="small"
                style={{
                  wordBreak: "break-all",
                  cursor: "pointer",
                }}
                title="Click to rename"
                onClick={() => handleStartRename(img)}
              >
                {img.id}
              </strong>
            )}
            <span className="small text-muted flex-shrink-0 ms-2">
              {formatFileSize(img.file_size)}
            </span>
          </div>
          <div className="small text-muted" style={{ fontSize: 11 }}>
            {formatTimestamp(img.file_timestamp)}
          </div>

          {/* Spacer to push buttons to bottom */}
          <div style={{ flex: 1 }} />

          {/* Row 2: icon buttons */}
          <div
            className="d-flex gap-2 mt-1"
            style={{
              borderTop: "1px solid var(--theme-border)",
              paddingTop: 4,
              marginTop: 4,
              flexWrap: "wrap",
            }}
          >
            <button
              type="button"
              title={moveFeedback === img.id ? "Sent to canvas" : "Move to canvas"}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 4,
                borderRadius: 4,
                opacity: 0.7,
                transition: "opacity 0.15s, background 0.15s",
                lineHeight: 1,
              }}
              onClick={() => handleMoveToCanvas(img)}
              onMouseEnter={(e) => {
                e.currentTarget.style.background =
                  "rgba(0,132,185,0.15)";
                e.currentTarget.style.opacity = "1";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "none";
                e.currentTarget.style.opacity = "0.7";
              }}
            >
              <img
                src="/icons/lucide/dark/panel-right-open.svg"
                alt="Move to canvas"
                style={{
                  width: 16,
                  height: 16,
                  filter: imgFilter,
                }}
              />
            </button>
            <button
              type="button"
              title="View details"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 4,
                borderRadius: 4,
                opacity: 0.7,
                transition: "opacity 0.15s, background 0.15s",
                lineHeight: 1,
              }}
              onClick={() => setPreviewIndex(idx)}
              onMouseEnter={(e) => {
                e.currentTarget.style.background =
                  "rgba(0,132,185,0.15)";
                e.currentTarget.style.opacity = "1";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "none";
                e.currentTarget.style.opacity = "0.7";
              }}
            >
              <img
                src="/icons/lucide/dark/info.svg"
                alt="View details"
                style={{
                  width: 16,
                  height: 16,
                  filter: imgFilter,
                }}
              />
            </button>
            <button
              type="button"
              title="Delete image"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 4,
                borderRadius: 4,
                opacity: 0.7,
                transition: "opacity 0.15s, background 0.15s",
                lineHeight: 1,
              }}
              onClick={() =>
                setConfirmDeleteId(
                  confirmDeleteId === img.id ? null : img.id,
                )
              }
              onMouseEnter={(e) => {
                e.currentTarget.style.background =
                  "rgba(0,132,185,0.15)";
                e.currentTarget.style.opacity = "1";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "none";
                e.currentTarget.style.opacity = "0.7";
              }}
            >
              <img
                src="/icons/lucide/dark/trash.svg"
                alt="Delete"
                style={{
                  width: 16,
                  height: 16,
                  filter: imgFilter,
                }}
              />
            </button>

            {confirmDeleteId === img.id && (
              <div className="d-flex gap-2 align-items-center">
                <span className="small text-muted">
                  Delete this image?
                </span>
                <button
                  title="Yes"
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: 4,
                    borderRadius: 4,
                    opacity: 0.7,
                    transition: "opacity 0.15s, background 0.15s",
                    lineHeight: 1,
                  }}
                  onClick={() =>
                    executeDelete(selectedDate ?? "", img.id)
                  }
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background =
                      "rgba(0,132,185,0.15)";
                    e.currentTarget.style.opacity = "1";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "none";
                    e.currentTarget.style.opacity = "0.7";
                  }}
                >
                  <img
                    src="/icons/lucide/dark/circle-check.svg"
                    alt="Yes"
                    style={{
                      width: 16,
                      height: 16,
                      filter: imgFilter,
                    }}
                  />
                </button>
                <button
                  title="No"
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: 4,
                    borderRadius: 4,
                    opacity: 0.7,
                    transition: "opacity 0.15s, background 0.15s",
                    lineHeight: 1,
                  }}
                  onClick={() => setConfirmDeleteId(null)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background =
                      "rgba(0,132,185,0.15)";
                    e.currentTarget.style.opacity = "1";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "none";
                    e.currentTarget.style.opacity = "0.7";
                  }}
                >
                  <img
                    src="/icons/lucide/dark/circle-x.svg"
                    alt="No"
                    style={{
                      width: 16,
                      height: 16,
                      filter: imgFilter,
                    }}
                  />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ── Render one local storage image row ─────────────────────────────

  const renderLocalRow = (entry: LocalImageEntry) => (
    <div
      key={`local-${entry.id}`}
      className="d-flex border rounded p-1 mb-1 align-items-start"
      style={{ backgroundColor: "rgba(255,255,255,0.02)" }}
    >
      {/* Thumbnail */}
      <div
        className="border rounded overflow-hidden flex-shrink-0"
        style={{ width: 96, height: 96 }}
      >
        <img
          src={entry.dataUrl}
          alt={entry.id}
          className="w-100 h-100"
          style={{ objectFit: "cover" }}
          loading="lazy"
        />
      </div>

      {/* Info */}
      <div className="ms-2 flex-grow-1 overflow-hidden">
        <div className="d-flex justify-content-between align-items-start">
          <strong className="small" style={{ wordBreak: "break-all" }}>
            {entry.id}
          </strong>
          <span className="small text-muted flex-shrink-0 ms-1">
            {formatFileSize(entry.fileSize)}
          </span>
        </div>

        <div className="small text-muted">
          Stored locally · {entry.timestamp}
          <Button
            variant="link"
            size="sm"
            className="p-0 ms-1 small text-danger"
            onClick={() => handleDeleteLocal(entry.id)}
            title="Delete local image"
          >
            Delete
          </Button>
        </div>

        {/* Local metadata */}
        {(entry.prompt || entry.seed || entry.steps) && (
          <div className="small text-muted mt-1" style={{ lineHeight: 1.4 }}>
            {entry.prompt && (
              <span className="me-2">
                <strong>prompt:</strong> {truncate(entry.prompt, 40)}{" "}
              </span>
            )}
            {entry.seed !== undefined && (
              <span className="me-2">
                <strong>seed:</strong> {entry.seed}{" "}
              </span>
            )}
            {entry.steps !== undefined && (
              <span className="me-2">
                <strong>steps:</strong> {entry.steps}{" "}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );

  // ── Render ──────────────────────────────────────────────────────────

  if (loadingDates) {
    return (
      <div className="p-2">
        <h6 className="text-muted mb-2">Image Browser</h6>
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
        {previewIndex !== null && (
          <ImagePreviewModal
            images={serverImages}
            currentIndex={previewIndex}
            onClose={() => setPreviewIndex(null)}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        )}
      </div>
    );
  }

  const hasLocalImages = localImages.length > 0;

  return (
    <div className="p-2 d-flex flex-column h-100">
      <h6 className="text-muted mb-2">Image Browser</h6>

      {/* Date dropdown with local storage option */}
      <select
        className="form-select form-select-sm mb-2"
        value={showLocal ? "__local__" : selectedDate ?? ""}
        onChange={handleDateChange}
      >
        {hasLocalImages && (
          <option value="__local__">
            Local Storage ({localImages.length})
          </option>
        )}
        {dates.length === 0 && !hasLocalImages && (
          <option value="">No images found</option>
        )}
        {dates.map((d) => (
          <option key={d.value} value={d.value}>
            {d.label}
          </option>
        ))}
      </select>

      {/* Image list */}
      <div className="flex-grow-1 overflow-auto">
        {showLocal ? (
          /* Local storage view */
          localImages.length === 0 ? (
            <p className="text-muted small text-center mt-3">
              No local images stored.
            </p>
          ) : (
            localImages.map(renderLocalRow)
          )
        ) : (
          /* Server images */
          <>
            {serverImages.length === 0 && !loadingImages ? (
              <p className="text-muted small text-center mt-3">
                No images for this date.
              </p>
            ) : (
              serverImages.map((img, idx) => renderServerRow(img, idx))
            )}

            {/* Sentinel for IntersectionObserver */}
            {hasMore && (
              <div ref={sentinelRef} className="py-2 text-center">
                {loadingImages ? (
                  <Spinner animation="border" size="sm" />
                ) : (
                  <span className="text-muted small">Scroll for more</span>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {!showLocal && (
        <div className="d-flex justify-content-between align-items-center mt-1">
          <div>
            {total > 0 && (
              <>
                {confirmDeleteAll ? (
                  <div className="d-flex gap-2 align-items-center">
                    <span className="small text-muted">
                      Delete all {total} images?
                    </span>
                    <button
                      title="Yes"
                      onClick={executeDeleteAll}
                      style={{
                        background: "none",
                        border: "none",
                        padding: 2,
                        cursor: "pointer",
                      }}
                    >
                      <img
                        src="/icons/lucide/dark/circle-check.svg"
                        alt="Yes"
                        style={{
                          width: 16,
                          height: 16,
                          filter: "var(--theme-icon-filter)",
                        }}
                      />
                    </button>
                    <button
                      title="No"
                      onClick={() => setConfirmDeleteAll(false)}
                      style={{
                        background: "none",
                        border: "none",
                        padding: 2,
                        cursor: "pointer",
                      }}
                    >
                      <img
                        src="/icons/lucide/dark/circle-x.svg"
                        alt="No"
                        style={{
                          width: 16,
                          height: 16,
                          filter: "var(--theme-icon-filter)",
                        }}
                      />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirmDeleteAll(true)}
                    title="Delete all images for this date"
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--bs-danger)",
                      fontSize: 12,
                      cursor: "pointer",
                      padding: 0,
                      textDecoration: "underline",
                      textUnderlineOffset: 2,
                    }}
                  >
                    Delete All
                  </button>
                )}
              </>
            )}
          </div>
          <div className="text-muted small text-end">
            {serverImages.length} / {total}
          </div>
        </div>
      )}

      {/* Image preview modal */}
      {previewIndex !== null && (
        <ImagePreviewModal
          images={serverImages}
          currentIndex={previewIndex}
          onClose={() => setPreviewIndex(null)}
          onPrev={handlePrev}
          onNext={handleNext}
        />
      )}
    </div>
  );
}

// Re-export helper so other components can save to local storage
export { saveLocalImage, getLocalImages, type LocalImageEntry };
