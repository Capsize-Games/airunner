import { useState, useEffect, useRef, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
import { BASE_URL } from "../../types/api";
import type { ImageDateInfo, ImageInfo } from "../../api/client";

const PAGE_SIZE = 20;
const LS_DATE_KEY = "airunner_image_browser_date";

export default function ImageBrowserPanel() {
  const [dates, setDates] = useState<ImageDateInfo[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(() => {
    try { return localStorage.getItem(LS_DATE_KEY); }
    catch { return null; }
  });
  const [images, setImages] = useState<ImageInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loadingDates, setLoadingDates] = useState(true);
  const [loadingImages, setLoadingImages] = useState(false);
  const [hasMore, setHasMore] = useState(true);

  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // ── Load dates on mount ─────────────────────────────────────────────

  const loadDates = useCallback(async () => {
    try {
      const { listImageDates } = await import("../../api/client");
      const data = await listImageDates();
      setDates(data.dates);
      if (data.dates.length > 0 && !selectedDate) {
        setSelectedDate(data.dates[0].value);
      } else if (selectedDate) {
        // Verify saved date still exists in the list
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

  // ── Load images for the selected date ───────────────────────────────

  const loadImages = useCallback(
    async (date: string, currentOffset: number, append: boolean) => {
      setLoadingImages(true);
      try {
        const { listImages } = await import("../../api/client");
        const data = await listImages(date, currentOffset, PAGE_SIZE);
        if (append) {
          setImages((prev) => [...prev, ...data.images]);
        } else {
          setImages(data.images);
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
    setImages([]);
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
          // Reload the currently selected date's images
          setImages([]);
          setOffset(0);
          setHasMore(true);
          if (selectedDate) {
            loadImages(selectedDate, 0, false);
          }
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
    setSelectedDate(val);
    if (val) {
      try { localStorage.setItem(LS_DATE_KEY, val); } catch {}
    } else {
      try { localStorage.removeItem(LS_DATE_KEY); } catch {}
    }
  };

  // ── Render ──────────────────────────────────────────────────────────

  if (loadingDates) {
    return (
      <div className="p-2">
        <h6 className="text-muted mb-2">Image Browser</h6>
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
      </div>
    );
  }

  return (
    <div className="p-2 d-flex flex-column h-100">
      <h6 className="text-muted mb-2">Image Browser</h6>

      {/* Date dropdown */}
      <select
        className="form-select form-select-sm mb-2"
        value={selectedDate ?? ""}
        onChange={handleDateChange}
      >
        {dates.length === 0 && <option value="">No dates found</option>}
        {dates.map((d) => (
          <option key={d.value} value={d.value}>
            {d.label}
          </option>
        ))}
      </select>

      {/* Thumbnail grid */}
      <div className="flex-grow-1 overflow-auto">
        {images.length === 0 && !loadingImages ? (
          <p className="text-muted small text-center mt-3">
            No images for this date.
          </p>
        ) : (
          <div
            className="d-flex flex-wrap gap-2"
            style={{ alignContent: "flex-start" }}
          >
            {images.map((img) => (
              <div
                key={img.id}
                className="border rounded overflow-hidden"
                style={{
                  width: 96,
                  height: 96,
                  cursor: "grab",
                  flexShrink: 0,
                }}
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
            ))}
          </div>
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
      </div>

      {total > 0 && (
        <div className="text-muted small text-end mt-1">
          {images.length} / {total}
        </div>
      )}
    </div>
  );
}
