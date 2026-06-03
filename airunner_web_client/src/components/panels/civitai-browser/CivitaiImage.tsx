import { useState, useEffect, useCallback } from "react";
import { BASE_URL } from "../../../types/api";

// CivitAI supports ?width=N in image URLs for smaller thumbnails
function resizeUrl(url: string, width: number): string {
  if (!url) return "";
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
          body: JSON.stringify({ url: fetchUrl, max_bytes: 5_000_000 }),
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
  }, [url, thumbWidth]);

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
    />
  );
}
