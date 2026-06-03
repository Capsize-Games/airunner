import { useState, useEffect, useCallback } from "react";
import { BASE_URL } from "../../../types/api";

// CivitAI supports ?width=N in image URLs for smaller thumbnails.
// The `original=true` parameter overrides width so we strip it.
function resizeUrl(url: string, width: number): string {
  if (!url) return "";
  // Remove original=true if present (it disables width)
  url = url.replace(/original=true[&]?/, "");
  url = url.replace(/[&?]$/, "");
  if (url.includes("width=")) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}width=${width}`;
}

interface CivitaiImageProps {
  url: string;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
  /** Request thumbnail at this width (default 120px for thumbnails) */
  thumbWidth?: number;
  /** Max bytes to accept from the proxy (thumbnails ~100KB, previews ~500KB) */
  maxBytes?: number;
}

/**
 * Fetches a CivitAI image through the daemon proxy and displays it as a blob URL.
 * Derived from the PySide6 ImageLoaderWorker pattern.
 * Adds width=N to the CivitAI URL for smaller payloads.
 */
export default function CivitaiImage({
  url,
  alt,
  className,
  style,
  thumbWidth = 120,
  maxBytes = 1_500_000, // 1.5MB default (CivitAI 120px can be ~300-800KB)
}: CivitaiImageProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  const fetchImage = useCallback(async () => {
    if (!url || url === "") {
      setFailed(true);
      return;
    }
    setFailed(false);
    // Request smaller version from CivitAI via width param
    const fetchUrl = resizeUrl(url, thumbWidth);
    try {
      const response = await fetch(
        `${BASE_URL}/api/v1/downloads/civitai/image`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: fetchUrl, max_bytes: maxBytes }),
        },
      );
      if (!response.ok) {
        setFailed(true);
        return;
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      setBlobUrl(objectUrl);
    } catch {
      setFailed(true);
    }
  }, [url, thumbWidth, maxBytes]);

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
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 10,
          color: "#666",
        }}
      >
        ✕
      </div>
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
      alt={alt}
      className={className}
      style={style}
      loading="lazy"
      onContextMenu={(e) => e.preventDefault()}
    />
  );
}
