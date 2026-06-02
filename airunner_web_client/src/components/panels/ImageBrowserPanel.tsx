import { useState, useEffect, useRef, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
import { BASE_URL } from "../../types/api";
import type { ImageDateInfo, ImageInfo } from "../../api/client";
import { deleteImage, renameImage } from "../../api/client";
import {
  getLocalImages,
  deleteLocalImage,
  saveLocalImage,
  LS_DATE_KEY,
  type LocalImageEntry,
} from "./image-browser/LocalImageHelpers";
import ImagePreviewModal from "./image-browser/ImagePreviewModal";
import ServerImageRow from "./image-browser/ServerImageRow";
import LocalImageRow from "./image-browser/LocalImageRow";
import ImageBrowserFooter from "./image-browser/ImageBrowserFooter";

const PAGE_SIZE = 20;

export { saveLocalImage, getLocalImages, type LocalImageEntry };

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
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);

  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setLocalImages(getLocalImages());
  }, []);

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
        setPreviewIndex(null);
      } catch {
        // unavailable
      } finally {
        setLoadingImages(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!selectedDate) return;
    setServerImages([]);
    setOffset(0);
    setHasMore(true);
    loadImages(selectedDate, 0, false);
  }, [selectedDate, loadImages]);

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

  const handleDeleteFromServer = (id: string) => {
    setServerImages((prev) => prev.filter((img) => img.id !== id));
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

  const handleDeleteLocal = (id: string) => {
    deleteLocalImage(id);
    setLocalImages(getLocalImages());
  };

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

      <div className="flex-grow-1 overflow-auto">
        {showLocal ? (
          localImages.length === 0 ? (
            <p className="text-muted small text-center mt-3">
              No local images stored.
            </p>
          ) : (
            localImages.map((entry) => (
              <LocalImageRow
                key={`local-${entry.id}`}
                entry={entry}
                onDelete={handleDeleteLocal}
              />
            ))
          )
        ) : (
          <>
            {serverImages.length === 0 && !loadingImages ? (
              <p className="text-muted small text-center mt-3">
                No images for this date.
              </p>
            ) : (
              serverImages.map((img, idx) => (
                <ServerImageRow
                  key={img.id}
                  img={img}
                  idx={idx}
                  selectedDate={selectedDate}
                  onPreview={setPreviewIndex}
                  onDeleted={handleDeleteFromServer}
                />
              ))
            )}

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
        <ImageBrowserFooter
          total={total}
          serverImagesCount={serverImages.length}
          confirmDeleteAll={confirmDeleteAll}
          onDeleteAll={executeDeleteAll}
          onConfirmDeleteAll={() => setConfirmDeleteAll(true)}
          onCancelDeleteAll={() => setConfirmDeleteAll(false)}
        />
      )}

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
