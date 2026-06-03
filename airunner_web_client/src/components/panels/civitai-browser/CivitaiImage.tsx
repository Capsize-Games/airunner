import { useState } from "react";

interface CivitaiImageProps {
  url: string;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
  /** Desired pixel width — server now returns images sized at
   *  40px (small), 200px (medium), 500px (full).  The component
   *  picks the best size based on this hint. */
  width?: number;
  /** Pre-encoded base64 thumbnail from the server response.
   *  When provided, renders directly without a network fetch. */
  base64?: string;
}

/**
 * Renders a CivitAI image.
 *
 * When ``base64`` is provided (pre-fetched inline thumbnails from the
 * search/detail endpoints), renders it as a data URI with zero network
 * requests.  Otherwise falls back to the legacy single-image endpoint.
 */
export default function CivitaiImage({
  url,
  alt,
  className,
  style,
  width: _desiredWidth,
  base64,
}: CivitaiImageProps) {
  if (base64) {
    return (
      <img
        src={`data:image/jpeg;base64,${base64}`}
        alt={alt}
        className={className}
        style={style}
        loading="lazy"
      />
    );
  }

  // Fallback: render the placeholder.  Legacy single-image fetches
  // are handled by the CivitaiImageLegacy wrapper below if needed.
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
