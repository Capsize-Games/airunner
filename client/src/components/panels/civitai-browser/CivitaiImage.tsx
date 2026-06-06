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
 * Priority:
 * 1. ``base64`` prop — data URI (zero network, used for inline thumbnails
 *    that the server embeds in search/detail JSON responses).
 * 2. Empty placeholder when no base64 is available.
 *
 * A failing image is silently hidden (no broken-image alt text).
 */
export default function CivitaiImage({
  url: _url,
  alt: _alt,
  className,
  style,
  width: _desiredWidth,
  base64,
}: CivitaiImageProps) {
  const [failed, setFailed] = useState(false);

  if (base64 && !failed) {
    return (
      <img
        src={`data:image/jpeg;base64,${base64}`}
        alt=""
        className={className}
        style={style}
        loading="lazy"
        onError={() => setFailed(true)}
      />
    );
  }

  /* ── Empty placeholder — never show alt text ── */
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
