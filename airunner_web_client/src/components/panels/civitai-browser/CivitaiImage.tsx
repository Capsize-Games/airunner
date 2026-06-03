import { useState, useEffect, useCallback, useRef } from "react";
import { BASE_URL } from "../../../types/api";

interface CivitaiImageProps {
  url: string;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
  /** Desired pixel width; server resizes + caches server-side */
  width?: number;
  /** Fallback if width not set */
  maxBytes?: number;
}

// ── Shared SSE connection (one EventSource for all components) ──

const _readyListeners = new Set<(url: string) => void>();
let _readySource: EventSource | null = null;

function ensureReadySource() {
  if (_readySource) return;
  _readySource = new EventSource(
    `${BASE_URL}/api/v1/downloads/civitai/images/ready`,
  );
  _readySource.addEventListener("message", (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "image_ready" && data.url) {
        _readyListeners.forEach((fn) => fn(data.url));
      }
    } catch { /* */ }
  });
  _readySource.onerror = () => { /* auto-reconnect */ };
}

function subscribeReady(fn: (url: string) => void) {
  _readyListeners.add(fn);
  ensureReadySource();
  return () => { _readyListeners.delete(fn); };
}

// ── Module-level cache: URL+width -> blob URL, shared across all instances ──

const _blobCache = new Map<string, string>();

function cacheKey(url: string, width?: number): string {
  return `${url}:${width ?? "full"}`;
}

/**
 * Fetches a CivitAI image through the daemon proxy.
 * Passes a ``width`` parameter so the server resizes + caches,
 * keeping response payloads small (~10-50KB for thumbnails).
 * Results are cached in-memory by URL+width to avoid redundant fetches.
 */
export default function CivitaiImage({
  url,
  alt,
  className,
  style,
  width: desiredWidth,
  maxBytes = 3_000_000,
}: CivitaiImageProps) {
  const key = cacheKey(url, desiredWidth);
  const [blobUrl, setBlobUrl] = useState<string | null>(
    () => _blobCache.get(key) ?? null,
  );
  const [failed, setFailed] = useState(false);

  // Subscribe to image-ready SSE (shared connection) for retry on failure
  useEffect(() => {
    const unsub = subscribeReady((readyUrl) => {
      if (readyUrl === url) {
        // Image now cached — retry the fetch
        fetchImage();
      }
    });
    return unsub;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  const fetchImage = useCallback(async () => {
    if (!url || url === "") {
      setFailed(true);
      return;
    }

    // Return cached blob URL if available
    const cached = _blobCache.get(key);
    if (cached) {
      setBlobUrl(cached);
      return;
    }

    setFailed(false);
    try {
      const body: Record<string, unknown> = { url, max_bytes: maxBytes };
      if (desiredWidth) body.width = desiredWidth;
      const response = await fetch(
        `${BASE_URL}/api/v1/downloads/civitai/image`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      if (!response.ok) {
        setFailed(true);
        return;
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      // Cache for future use
      _blobCache.set(key, objectUrl);
      setBlobUrl(objectUrl);
    } catch {
      setFailed(true);
    }
  }, [url, key, desiredWidth, maxBytes]);

  useEffect(() => {
    fetchImage();
  }, [fetchImage]);

  if (failed) {
    return (
      <div
        className={className}
        style={{
          ...style,
          background: "var(--theme-bg-secondary)",
        }}
      />
    );
  }

  if (!blobUrl) {
    return (
      <div
        className={className}
        style={{
          ...style,
          background: "var(--theme-bg-secondary)",
        }}
      />
    );
  }

  return (
    <img
      src={blobUrl}
      alt=""
      className={className}
      style={style}
      loading="lazy"
    />
  );
}
