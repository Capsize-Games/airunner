import { useState, useEffect, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
import type { ImageInfo } from "../../api/client";
import { deleteImage } from "../../api/client";
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
import ImageDateSelector from "./image-browser/ImageDateSelector";
import { useInfiniteScroll } from "./image-browser/useInfiniteScroll";
import { useImageBrowserSSE } from "./image-browser/useImageBrowserSSE";
import { useImageDates } from "../../hooks/useImageDates";
import { useLocalStorage } from "../../hooks/useLocalStorage";

const PAGE_SIZE = 20;

export { saveLocalImage, getLocalImages, type LocalImageEntry };

export default function ImageBrowserPanel() {
  const { dates, loading: loadingDates, reload: reloadDates } = useImageDates();
  const [selectedDate, setSelectedDate] = useLocalStorage<string | null>(LS_DATE_KEY, null);
  const [serverImages, setServerImages] = useState<ImageInfo[]>([]);
  const [localImages, setLocalImages] = useState<LocalImageEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loadingImages, setLoadingImages] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [showLocal, setShowLocal] = useState(false);
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);

  useEffect(() => {
    setLocalImages(getLocalImages());
  }, []);

  // Auto-select first date when dates load and nothing is selected.
  useEffect(() => {
    if (dates.length === 0) return;
    if (!selectedDate) {
      setSelectedDate(dates[0].value);
    } else {
      const stillExists = dates.some((d) => d.value === selectedDate);
      if (!stillExists) setSelectedDate(dates[0].value);
    }
  }, [dates]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const loadMore = useCallback(() => {
    if (hasMore && !loadingImages && selectedDate) {
      loadImages(selectedDate, offset, true);
    }
  }, [hasMore, loadingImages, selectedDate, offset, loadImages]);

  const sentinelRef = useInfiniteScroll(loadMore, hasMore && !loadingImages);

  const handleSSEReload = useCallback(() => {
    reloadDates();
    setServerImages([]);
    setOffset(0);
    setHasMore(true);
    if (selectedDate) {
      loadImages(selectedDate, 0, false);
    }
    setLocalImages(getLocalImages());
  }, [reloadDates, selectedDate, loadImages]);

  useImageBrowserSSE(handleSSEReload);

  const handleDateChange = (val: string | null, isLocal: boolean) => {
    if (isLocal) {
      setShowLocal(true);
      return;
    }
    setShowLocal(false);
    setSelectedDate(val);
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

  return (
    <div className="p-2 d-flex flex-column h-100">
      <ImageDateSelector
        dates={dates}
        selectedDate={selectedDate}
        showLocal={showLocal}
        localImageCount={localImages.length}
        onChange={handleDateChange}
      />

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
