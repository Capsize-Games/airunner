import { useState, useEffect, useCallback } from "react";
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

/**
 * Fetches a CivitAI image through the daemon proxy.
 * Passes a ``width`` parameter so the server resizes + caches,
 * keeping response payloads small (~10-50KB for thumbnails).
 */
export default function CivitaiImage({
  url,
  alt,
  className,
  style,
  width: desiredWidth,
  maxBytes = 3_000_000,
}: CivitaiImageProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  const fetchImage = useCallback(async () => {
    if (!url || url === "") {
      setFailed(true);
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
      setBlobUrl(objectUrl);
    } catch {
      setFailed(true);
    }
  }, [url, desiredWidth, maxBytes]);

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
