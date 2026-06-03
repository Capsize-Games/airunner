import { useState, useEffect, useCallback } from "react";
import { BASE_URL } from "../../../types/api";

interface CivitaiImageProps {
  url: string;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
  /** Max bytes to accept from the proxy */
  maxBytes?: number;
}

/**
 * Fetches a CivitAI image through the daemon proxy and displays it
 * as a blob URL. The CivitAI URL is passed as-is to the proxy which
 * enforces the max_bytes limit server-side.
 */
export default function CivitaiImage({
  url,
  alt,
  className,
  style,
  maxBytes = 2_000_000, // 2MB default
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
      const response = await fetch(
        `${BASE_URL}/api/v1/downloads/civitai/image`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, max_bytes: maxBytes }),
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
  }, [url, maxBytes]);

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
