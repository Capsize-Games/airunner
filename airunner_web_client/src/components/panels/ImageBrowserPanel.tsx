import { useState, useEffect, useRef, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
import Button from "react-bootstrap/Button";
import { BASE_URL } from "../../types/api";
import type { ImageDateInfo, ImageInfo } from "../../api/client";

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

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen) + "...";
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
  const [expandedMeta, setExpandedMeta] = useState<Record<string, boolean>>({});
  const [showLocal, setShowLocal] = useState(false);

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

  // ── Metadata expand toggle ──────────────────────────────────────────

  const toggleMeta = (id: string) => {
    setExpandedMeta((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // ── Open file path in system file manager ───────────────────────────

  const handleOpenFile = async (filePath: string) => {
    try {
      // Attempt to open via the backend's open-file endpoint
      await fetch(`${BASE_URL}/api/v1/system/open-file`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: filePath }),
      });
    } catch {
      // fallback: copy path to clipboard
      try {
        await navigator.clipboard.writeText(filePath);
      } catch {
        // ignore
      }
    }
  };

  // ── Delete local image ──────────────────────────────────────────────

  const handleDeleteLocal = (id: string) => {
    deleteLocalImage(id);
    setLocalImages(getLocalImages());
  };

  // ── Render metadata as clickable chips ──────────────────────────────

  const renderMetadata = (
    meta: Record<string, unknown> | null,
    imgId: string,
  ) => {
    if (!meta) {
      return (
        <span className="text-muted small">No metadata</span>
      );
    }

    const isExpanded = expandedMeta[imgId];
    // Pick the most interesting keys to show
    const displayedFields: Record<string, unknown> = {};
    const extraFields: Record<string, unknown> = {};
    const priorityKeys = [
      "prompt", "negative_prompt", "seed", "steps",
      "scale", "model", "scheduler", "version",
    ];

    for (const key of priorityKeys) {
      if (key in meta) {
        displayedFields[key] = meta[key];
      }
    }
    // Remaining keys go to extra
    for (const [k, v] of Object.entries(meta)) {
      if (!(k in displayedFields)) {
        extraFields[k] = v;
      }
    }

    const entries = isExpanded
      ? { ...displayedFields, ...extraFields }
      : displayedFields;

    return (
      <div className="small text-muted" style={{ lineHeight: 1.4 }}>
        {Object.entries(entries).map(([key, value]) => {
          const valStr =
            typeof value === "object"
              ? JSON.stringify(value)
              : String(value);
          return (
            <span key={key} className="me-2" title={`${key}: ${valStr}`}>
              <strong>{key}:</strong>{" "}
              {truncate(valStr, 40)}{" "}
            </span>
          );
        })}
        {Object.keys(extraFields).length > 0 && (
          <Button
            variant="link"
            size="sm"
            className="p-0 small text-light"
            onClick={() => toggleMeta(imgId)}
          >
            {isExpanded ? "▲ less" : "▼ more"}
          </Button>
        )}
      </div>
    );
  };

  // ── Render one server image row ────────────────────────────────────

  const renderServerRow = (img: ImageInfo) => (
    <div
      key={img.id}
      className="d-flex border rounded p-1 mb-1 align-items-start"
      style={{ backgroundColor: "rgba(255,255,255,0.02)" }}
    >
      {/* Thumbnail */}
      <div
        className="border rounded overflow-hidden flex-shrink-0"
        style={{ width: 96, height: 96, cursor: "grab" }}
        title={img.id}
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
      <div className="ms-2 flex-grow-1 overflow-hidden">
        <div className="d-flex justify-content-between align-items-start">
          <strong className="small" style={{ wordBreak: "break-all" }}>
            {img.id}
          </strong>
          <span className="small text-muted flex-shrink-0 ms-1">
            {formatFileSize(img.file_size)}
          </span>
        </div>

        <div className="d-flex align-items-center small text-muted">
          <span
            className="text-truncate d-inline-block"
            style={{ maxWidth: "240px" }}
            title={img.file_path}
          >
            {img.file_path}
          </span>
          <Button
            variant="link"
            size="sm"
            className="p-0 ms-1 small text-light flex-shrink-0"
            onClick={() => handleOpenFile(img.file_path)}
            title="Open file location"
          >
            Open
          </Button>
        </div>

        <div className="mt-1">
          {renderMetadata(img.metadata, img.id)}
        </div>
      </div>
    </div>
  );

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
              serverImages.map(renderServerRow)
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

      {!showLocal && total > 0 && (
        <div className="text-muted small text-end mt-1">
          {serverImages.length} / {total}
        </div>
      )}
    </div>
  );
}

// Re-export helper so other components can save to local storage
export { saveLocalImage, getLocalImages, type LocalImageEntry };
