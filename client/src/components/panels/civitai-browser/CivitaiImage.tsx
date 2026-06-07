import { useState, useEffect } from "react";

interface CivitaiImageProps {
  url: string;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
  width?: number;
  base64?: string;
}

/**
 * Renders a CivitAI image.
 *
 * - ``base64`` prop → data URI (from streaming events or server embeds).
 * - Spinner while waiting for ``base64`` to arrive.
 * - Fallback icon after a timeout when ``base64`` never materialises.
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

  /* ── Hide spinner after 15 s, show placeholder icon ── */
  const [timedOut, setTimedOut] = useState(false);
  useEffect(() => {
    if (base64) { setTimedOut(false); return; }
    const id = setTimeout(() => setTimedOut(true), 15_000);
    return () => clearTimeout(id);
  }, [base64]);

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

  if (timedOut || failed) {
    return (
      <div
        className={className}
        style={{
          ...style,
          background: "var(--theme-bg-secondary)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg
          viewBox="0 0 24 24"
          width={16}
          height={16}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: "var(--theme-text-secondary)", opacity: 0.4 }}
        >
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
      </div>
    );
  }

  return (
    <div
      className={className}
      style={{
        ...style,
        background: "var(--theme-bg-secondary)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        className="spinner-border spinner-border-sm"
        role="status"
        style={{ color: "var(--bs-primary)" }}
      >
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  );
}
